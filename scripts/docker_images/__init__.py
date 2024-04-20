import json
import os
from pathlib import Path
from re import sub
from typing import NamedTuple, List, Optional

import asyncclick as click
import yaml

DEFAULT_STACKPACK_DIRECTORY = "./stackpacks"
DEFAULT_COMMON_STACKPACK_DIRECTORY = "./stackpacks_common"


class ImageDetails(NamedTuple):
    stackpack_id: str
    image_name: str
    version: str
    ecr_repo_name: str
    dockerfile: str
    context: str
    platform: str = None


@click.group()
async def docker_images():
    pass


@docker_images.command()
@click.option(
    "--stackpacks-dir",
    help="The directory containing the stackpacks. (multiple directories can be specified)",
    multiple=True,
    default=[DEFAULT_STACKPACK_DIRECTORY, DEFAULT_COMMON_STACKPACK_DIRECTORY],
    type=str,
)
async def detect(stackpacks_dir):
    image_details: List[ImageDetails] = []
    for spd in stackpacks_dir:
        image_details += await detect_images(
            stackpacks_directory=spd,
        )

    print(json.dumps([d._asdict() for d in image_details], indent=2))


@docker_images.command()
@click.option(
    "--stackpacks-dir",
    help="The directory containing the stackpacks. (multiple directories can be specified)",
    multiple=True,
    default=[DEFAULT_STACKPACK_DIRECTORY, DEFAULT_COMMON_STACKPACK_DIRECTORY],
    type=str,
)
@click.option(
    "--output-dir",
    help="The directory to write the pulumi program to.",
    prompt="Enter the output directory for the pulumi program.",
    type=str,
)
@click.option(
    "--repo-suffix",
    help="The suffix to append to the ECR repository name.",
    default="",
    type=str,
)
@click.option(
    "--whatif",
    help="Generate pulumi program to build and push docker images.",
    is_flag=True,
)
@click.option("--image", type=str)
async def generate(stackpacks_dir, output_dir, repo_suffix, whatif, image):
    # iterate through all subdirectories of the ./stackpacks directory
    # and grab the stackpack.yaml file
    # for each stackpack.yaml file extract the id and version.
    # then use the id and version to create an ECR repository name and tag
    # finally, generate a pulumi program that will build and push each docker image to its respective ECR repository.

    # Iterate through all subdirectories of the ./stackpacks directory
    image_details: List[ImageDetails] = []
    for spd in stackpacks_dir:
        image_details += await detect_images(
            stackpacks_directory=spd,
            output_directory=output_dir,
            repo_suffix=repo_suffix,
        )
    if image:
        image_details = [img for img in image_details if img.ecr_repo_name == image]

    if whatif:
        print(yaml.dump([i._asdict() for i in image_details]))
    app = generate_pulumi_program(image_details)
    if whatif:
        print(app)
    else:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        write_pulumi_program(app=app, output_dir=output_dir, suffix=repo_suffix)
    # Generate a pulumi program that will build and push each docker image to its respective ECR repository


def write_pulumi_program(app, output_dir, suffix=""):
    suffix = suffix or ""
    pulumi_yaml = f"""
name: stacksnap-docker-images{suffix}
runtime: nodejs
description: "A Pulumi program that builds and pushes StackSnap docker images to ECR repositories."
config:
  pulumi:tags:
    value:
      pulumi:template: ""
"""
    with open(f"{output_dir}/Pulumi.yaml", "w") as pulumi_file:
        pulumi_file.write(pulumi_yaml)

    with open(f"{output_dir}/index.ts", "w") as pulumi_file:
        pulumi_file.write(app)

    # copy over package.json and tsconfig.json
    os.system(f"cp {Path(__file__).parent}/package.json {output_dir}/package.json")
    os.system(f"cp {Path(__file__).parent}/tsconfig.json {output_dir}/tsconfig.json")


def generate_pulumi_program(image_details: List[ImageDetails]):
    print("Generating pulumi program for the following images:")
    for image_detail in image_details:
        print(
            f"- Stackpack ID: {image_detail.stackpack_id}, Image Name: {image_detail.image_name}, Version: {image_detail.version}"
        )
    pulumi_program = f"""
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as docker from "@pulumi/docker";

const ecrPublicAuth = aws.ecrpublic.getAuthorizationToken({{}});

"""
    for image_detail in image_details:
        camel_case_repo = camel_case(image_detail.ecr_repo_name)
        repo_var = f"{camel_case_repo}Repository"
        image_var = f"{camel_case_repo}Image"
        pulumi_program += f"""
        
// Create an ECR repository.
const {repo_var} = new aws.ecrpublic.Repository("{image_detail.ecr_repo_name}", {{
    repositoryName: "{image_detail.ecr_repo_name}",
    forceDestroy: true,
    tags: {{
        stackpack_id: "{image_detail.stackpack_id}",
        image_name: "{image_detail.image_name}",
    }}
}});

// Build and publish the Docker image to the ECR repository.
const {image_var} = new docker.Image("{image_detail.ecr_repo_name}:{image_detail.version}", {{
    build: {{
        context: "{image_detail.context}",
        dockerfile: "{image_detail.dockerfile}",
        platform: "{image_detail.platform or "linux/amd64"}",
    }},
    imageName: pulumi.interpolate`${{{repo_var}.repositoryUri}}:{image_detail.version}`,
    registry: {{
        password: pulumi.secret(
          ecrPublicAuth.then((authToken) => authToken.password),
        ),
        username: ecrPublicAuth.then((authToken) => authToken.userName),
        server: {repo_var}.repositoryUri,
    }},
}},
);
"""
    return pulumi_program


def camel_case(s):
    s = sub(r"([_\-])+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


async def detect_images(
    stackpacks_directory,
    output_directory: Optional[str] = None,
    repo_suffix: Optional[str] = "",
):
    image_details: List[ImageDetails] = []
    for root, dirs, files in os.walk(stackpacks_directory):
        for file in files:
            # Grab the stackpack.yaml file
            if file == f"{Path(root).name}.yaml" or file == "common.yaml":
                file_path = os.path.join(root, file)

                with open(file_path, "r") as stream:
                    data = {}
                    try:
                        data: dict = yaml.safe_load(stream)
                    except yaml.YAMLError as exc:
                        print(exc)

                    stackpack_id = data.get("id")
                    version = data.get("version")
                    # extract all <root>:resources:DockerImage:Dockerfile properties from the stackpack.yaml file
                    if not isinstance(data, dict):
                        raise ValueError(
                            "Invalid stackpack.yaml file: root must be a dictionary"
                        )
                    if "docker_images" not in data:
                        continue
                    for image_name, props in data.get("docker_images", {}).items():
                        props = props or {}
                        dockerfile_prop = props.get("Dockerfile", "Dockerfile")
                        context = (
                            str(
                                os.path.relpath(
                                    Path(root) / props.get("Context", ""),
                                    output_directory,
                                )
                            )
                            if output_directory
                            else str(Path(root) / props.get("Context", ""))
                        )
                        context_dockerfile_path = str(Path(context) / dockerfile_prop)

                        cli_dockerfile_path = (
                            Path(root) / props.get("Context", "") / dockerfile_prop
                        )
                        if not os.path.exists(cli_dockerfile_path):
                            print(f"Could not find Dockerfile for {image_name}")
                            continue

                        print(f"Found Dockerfile for {image_name}")
                        ecr_repo_name = (
                            f"{stackpack_id}-{image_name}"
                            if stackpack_id != image_name
                            else stackpack_id
                        )
                        if repo_suffix:
                            ecr_repo_name = f"{ecr_repo_name}{repo_suffix}"
                        image_details.append(
                            ImageDetails(
                                stackpack_id=stackpack_id,
                                image_name=image_name,
                                version=version,
                                ecr_repo_name=ecr_repo_name,
                                dockerfile=context_dockerfile_path,
                                context=context,
                                platform=props.get("platform"),
                            )
                        )
    return image_details
