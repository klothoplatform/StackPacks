# stacksnap

<!-- TOC -->
* [stacksnap](#stacksnap)
  * [Development](#development)
    * [WSL2](#wsl2)
  * [Format](#format)
  * [CLI](#cli)
  * [Personal Stacks](#personal-stacks)
  * [Docker Images](#docker-images)
    * [Using a Custom Docker Image](#using-a-custom-docker-image)
      * [Declaring Custom Docker Images](#declaring-custom-docker-images)
      * [Referencing Custom Docker Images](#referencing-custom-docker-images)
      * [Configuring Docker Image Resolution](#configuring-docker-image-resolution)
    * [Building and Pushing Docker Images](#building-and-pushing-docker-images)
    * [Versioning Docker Images](#versioning-docker-images)
<!-- TOC -->


## Development

### WSL2
When developing on WSL2, use the [wsl-compose.yml](./wsl-compose.yml) file to start the backend's dependencies.

This file overrides incompatible settings like volume for dynamodb-local.

Example:

```shell
docker compose -f wsl-compose.yml up -d
```


## Format

```yaml
name: # The human-readable name of the stack pack
version: # Semver version of the stack pack, not used for now, but will be used in the future

base: # These are the default, basic features of the stack pack
  # Resources are a map from the resource ID to Properties. These will get converted
  # into constraints (both application & resource)
  resources:
    aws:type:name:
      LoadBalancers[0].ContainerPort: 8065 # Properties are in "constraint" format, not in template (ie, nested) format
      Cpu: ${CPU} # Can use configuration variables (see below)
  edges: # Edges are more-or-less the same as in resources.yaml and get converted to edge constraints
    aws:a:b -> aws:x:y:
  files: # Files describe files that need to be copied into the output folder.
    Dockerfile:
    .env:
      template: true # If true, the file is a template and will be rendered with the configuration

configuration:
  CPU: # This is an example of a value used in the base config
    name: # The human-readable name of the configuration value
    description: # Description of the configuration for the UI
    type: # The type of the configuration value (string, int, float, boolean, enum)
    default: # The default value of the configuration, required if used in the `base` section
    validation: # Validation rules based on the type
    initial_only: # Whether the value can only be set on initial configuration

  XYZ:
    type: boolean
    default: false
    values: # Values can be used as a "switch" for boolean or enum types
      true: # the "if" or "case" value
        # The contents are the same struct used in the `base` section
        resources:
          aws:s3_bucket:xyz-s3:
        edges:
          aws:ecs_service:svc -> aws:s3_bucket:xyz:

  DBPassword:
    name: Database Password
    type: string
    pulumi_key: # The pulumi config key to use for this value, set before the 'pulumi up'
```


## CLI

To generate infrastructure output from a stackpack file run from the root of the project
```sh
PYTHONPATH=. python3.11 scripts/cli.py iac generate-iac --file ./path/to/file.yaml --config ./path/to/config.json --project-name sample-project --output-dir output
```


## Personal Stacks

To create the setup for you personal stack:
```
mdkir personal
cp deploy/stacksnap.yaml personal/stacksnap.yaml
```

Make any modifications to the personal/stacksnap.yaml, including
```
REMOVE ALIAS
    aws:cloudfront_distribution:stacksnap-distribution:
      # TODO: figure out a way to make this less brittle
      Aliases:
        - dev.stacksnap.io

MODIFY EMAIL (IF NECESSARY)
    aws:ses_email_identity:stacksnap-email-identity:
      EmailIdentity: stacksnap@klo.dev
```

To generate infra directory, run:
```
ENGINE_PATH=/path/to/engine IAC_PATH=/path/to/iac make generate-personal-infra
```

To deploy, run:
```
KLOTHO_DIR=../klotho STACK_NAME=MY-STACK PULUMI_ACCESS_TOKEN=${ACCESS_TOKEN} REGION=us-east-2 make deploy-personal-infra
```

## Docker Images

Docker images referenced by StackPacks must either be pulled from a public registry or built
and pushed to ECR using the process described below.

### Using a Custom Docker Image


#### Declaring Custom Docker Images
Custom Docker images can be declared in the `docker_images` section of the StackPack file.
The `docker_images` section is a map from image name to build configuration.
    
    ```yaml
    id: my-stack
    version: 0.1.0
    docker_images:
      my-image:
        Dockerfile: path/to/Dockerfile
        Context: path/to/context  
      my-other-image:
        # inferred
        # Dockerfile: ./Dockerfile
        # Context: .
    ```

The resulting image's repository will be a combination of the StackPack ID and the image name.
If the image name matches the StackPack ID, the repository will be the StackPack ID.

The image will be tagged with the StackPack version.

Context is relative to the current file's directory.

#### Referencing Custom Docker Images
Custom Docker images can be referenced in the `resources` section of the StackPack file using the following format:

```yaml
resources:
  aws:ecs_task_definition:my-task:
    ContainerDefinitions[0].Image: ${docker_image:my-image}
```

In the example above, `${docker_image:my-image}` will be replaced with the URI of the Docker image in the ECR repository by the backend at run time during the constraint generation process.

#### Configuring Docker Image Resolution
The backend will attempt to resolve custom Docker image URIs by substituting the following variables in the following format:

`<ECR_REGISTRY>/<IMAGE_NAME><ECR_SUFFIX>:<VERSION>`

- **AWS_ACCOUNT** - The ID of the AWS account that stacksnap is deployed in. This ID will also be used as part of the ECR registry URI for custom Docker images.
- **IMAGE_NAME** - The image name. This is the name of the image as declared in the `docker_images` section of the StackPack file, including the StackPack ID prefix.
- **ECR_SUFFIX** - The suffix to append to the image name. This is an optional variable that can be set as an environment variable.
- **VERSION** - The version of the image. This is the version of the StackPack.


### Building and Pushing Docker Images

To build and push a Docker image to ECR, run one of the following commands (depending on the environment):

**Local**
```sh
make dockergen-local
```

**Dev**
```sh
make dockergen-dev
```

**Prod**
```sh
make dockergen-prod
```

This will generate a Pulumi program that builds and pushes all custom Docker images declared in the StackPack files to ECR.
The program will be output in the `docker_images/<ENVIRONMENT>` directory.

Create a stack and run `pulumi up` to deploy the Docker images to ECR.

### Versioning Docker Images

When making a change to an existing Docker image, running `pulumi up` without modifying the StackPack version will overwrite the existing image tag in ECR with the new image.

To create a new version of the Docker image, increment the StackPack version in the StackPack file and run `pulumi up` to push the new image to ECR with the new version tag.