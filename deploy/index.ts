import * as aws from "@pulumi/aws";
import * as awsInputs from "@pulumi/aws/types/input";
import * as command from "@pulumi/command";
import * as docker from "@pulumi/docker";
import * as inputs from "@pulumi/aws/types/input";
import * as pulumi from "@pulumi/pulumi";
import { OutputInstance } from "@pulumi/pulumi";
import { createALBAlarms, createCustomAlarms } from "./monitoring";

const kloConfig = new pulumi.Config("klo");
const protect = kloConfig.getBoolean("protect") ?? false;
const awsConfig = new pulumi.Config("aws");
const awsProfile = awsConfig.get("profile");
const accountId = pulumi.output(aws.getCallerIdentity({}));
const region = pulumi.output(aws.getRegion({}));


const cloudfront_origin_access_identity_0 =
  new aws.cloudfront.OriginAccessIdentity(
    "cloudfront_origin_access_identity-0",
    {
      comment:
        "this is needed to set up S3 polices so that the S3 bucket is not public",
    },
  );
const project_applications = new aws.dynamodb.Table(
  "project-applications",
  {
    attributes: [
      {
        name: "project_id",
        type: "S",
      },
      {
        name: "range_key",
        type: "S",
      },
    ],

    hashKey: "project_id",
    rangeKey: "range_key",
    billingMode: "PAY_PER_REQUEST",
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "project-applications",
    },
  },
  { protect: protect },
);
const projects = new aws.dynamodb.Table(
  "projects",
  {
    attributes: [
      {
        name: "id",
        type: "S",
      },
    ],

    hashKey: "id",
    billingMode: "PAY_PER_REQUEST",
    tags: { GLOBAL_KLOTHO_TAG: "stacksnap-dev", RESOURCE_NAME: "projects" },
  },
  { protect: protect },
);
const pulumi_stacks = new aws.dynamodb.Table(
  "pulumi-stacks",
  {
    attributes: [
      {
        name: "project_name",
        type: "S",
      },
      {
        name: "name",
        type: "S",
      },
    ],

    hashKey: "project_name",
    rangeKey: "name",
    billingMode: "PAY_PER_REQUEST",
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "pulumi-stacks",
    },
  },
  { protect: protect },
);
const workflow_jobs = new aws.dynamodb.Table(
  "workflow-jobs",
  {
    attributes: [
      {
        name: "partition_key",
        type: "S",
      },
      {
        name: "job_number",
        type: "N",
      },
    ],

    hashKey: "partition_key",
    rangeKey: "job_number",
    billingMode: "PAY_PER_REQUEST",
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "workflow-jobs",
    },
  },
  { protect: protect },
);
const workflow_runs = new aws.dynamodb.Table(
  "workflow-runs",
  {
    attributes: [
      {
        name: "project_id",
        type: "S",
      },
      {
        name: "range_key",
        type: "S",
      },
    ],

    hashKey: "project_id",
    rangeKey: "range_key",
    billingMode: "PAY_PER_REQUEST",
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "workflow-runs",
    },
  },
  { protect: protect },
);
const alarm_reporter_ecr_repo = new aws.ecr.Repository(
  "alarm_reporter-ecr_repo",
  {
    imageScanningConfiguration: {
      scanOnPush: true,
    },
    imageTagMutability: "MUTABLE",
    forceDelete: true,
    encryptionConfigurations: [{ encryptionType: "KMS" }],
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "alarm_reporter-ecr_repo",
    },
  },
);
const stacksnap_task_image_ecr_repo = new aws.ecr.Repository(
  "stacksnap-task-image-ecr_repo",
  {
    imageScanningConfiguration: {
      scanOnPush: true,
    },
    imageTagMutability: "MUTABLE",
    forceDelete: true,
    encryptionConfigurations: [{ encryptionType: "KMS" }],
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-task-image-ecr_repo",
    },
  },
);
const stacksnap_ecs_cluster = new aws.ecs.Cluster("stacksnap-ecs-cluster", {
  settings: [{ name: "containerInsights", value: "enabled" }],
  tags: {
    GLOBAL_KLOTHO_TAG: "stacksnap-dev",
    RESOURCE_NAME: "stacksnap-ecs-cluster",
  },
});
const subnet_0_route_table_nat_gateway_elastic_ip = new aws.ec2.Eip(
  "subnet-0-route_table-nat_gateway-elastic_ip",
  {
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "subnet-0-route_table-nat_gateway-elastic_ip",
    },
  },
);
const subnet_1_route_table_nat_gateway_elastic_ip = new aws.ec2.Eip(
  "subnet-1-route_table-nat_gateway-elastic_ip",
  {
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "subnet-1-route_table-nat_gateway-elastic_ip",
    },
  },
);
const stacksnap_ecs_launch_template_iam_instance_profb0be8bf5 =
  new aws.iam.Role("stacksnap-ecs-launch-template-iam_instance_profb0be8bf5", {
    assumeRolePolicy: pulumi.jsonStringify({
      Statement: [
        {
          Action: ["sts:AssumeRole"],
          Effect: "Allow",
          Principal: { Service: ["ec2.amazonaws.com"] },
        },
      ],
      Version: "2012-10-17",
    }),
    inlinePolicies: [
      {
        name: "stacksnap-ecs-launch-template-iam_instance_profile-instanceProfilePolicy",
        policy: pulumi.jsonStringify({
          Statement: [
            {
              Action: [
                "iam:ListInstanceProfiles",
                "ec2:Describe*",
                "ec2:Search*",
                "ec2:Get*",
              ],
              Effect: "Allow",
              Resource: ["*"],
            },
            {
              Action: ["iam:PassRole"],
              Condition: {
                StringEquals: { "iam:PassedToService": "ec2.amazonaws.com" },
              },
              Effect: "Allow",
              Resource: ["*"],
            },
          ],
        }),
      },
    ],
    managedPolicyArns: [
      ...[
        "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role",
      ],
    ],
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-ecs-launch-template-iam_instance_profb0be8bf5",
    },
  });
const alarm_reporter_log_group = new aws.cloudwatch.LogGroup(
  "alarm_reporter-log-group",
  {
    name: "/aws/lambda/alarm_reporter",
    retentionInDays: 5,
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "alarm_reporter-log-group",
    },
  },
);
const stacksnap_task_log_group = new aws.cloudwatch.LogGroup(
  "stacksnap-task-log-group",
  {
    name: "/aws/ecs/stacksnap-task",
    retentionInDays: 5,
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-task-log-group",
    },
  },
);
const region_0 = pulumi.output(aws.getRegion({}));
const stacksnap_binaries = new aws.s3.Bucket(
  "stacksnap-binaries",
  {
    forceDestroy: true,
    serverSideEncryptionConfiguration: {
      rule: {
        applyServerSideEncryptionByDefault: {
          sseAlgorithm: "aws:kms",
        },
        bucketKeyEnabled: true,
      },
    },
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-binaries",
    },
  },
  { protect: protect },
);
export const stacksnap_binaries_BucketName = stacksnap_binaries.bucket;
const stacksnap_iac_store = new aws.s3.Bucket(
  "stacksnap-iac-store",
  {
    forceDestroy: true,
    serverSideEncryptionConfiguration: {
      rule: {
        applyServerSideEncryptionByDefault: {
          sseAlgorithm: "aws:kms",
        },
        bucketKeyEnabled: true,
      },
    },
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-iac-store",
    },
  },
  { protect: protect },
);
export const stacksnap_iac_store_BucketName = stacksnap_iac_store.bucket;
const stacksnap_pulumi_state_bucket = new aws.s3.Bucket(
  "stacksnap-pulumi-state-bucket",
  {
    forceDestroy: true,
    serverSideEncryptionConfiguration: {
      rule: {
        applyServerSideEncryptionByDefault: {
          sseAlgorithm: "aws:kms",
        },
        bucketKeyEnabled: true,
      },
    },
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-pulumi-state-bucket",
    },
  },
  { protect: protect },
);
export const stacksnap_pulumi_state_bucket_BucketName =
  stacksnap_pulumi_state_bucket.bucket;
const stacksnap_ui = new aws.s3.Bucket(
  "stacksnap-ui",
  {
    forceDestroy: true,
    serverSideEncryptionConfiguration: {
      rule: {
        applyServerSideEncryptionByDefault: {
          sseAlgorithm: "AES256",
        },
        bucketKeyEnabled: true,
      },
    },
    tags: { GLOBAL_KLOTHO_TAG: "stacksnap-dev", RESOURCE_NAME: "stacksnap-ui" },
  },
  { protect: protect },
);
export const stacksnap_ui_BucketName = stacksnap_ui.bucket;
const stacksnap_pulumi_access_token = new aws.secretsmanager.Secret(
  "stacksnap-pulumi-access-token",
  {
    name: "stacksnap-pulumi-access-token",
    recoveryWindowInDays: 0,
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-pulumi-access-token",
    },
  },
  { protect: protect },
);
const stacksnap_email_identity = new aws.ses.EmailIdentity(
  "stacksnap-email-identity",
  {
    email: "stacksnap@klo.dev",
  },
);
const alarm_actions_topic = new aws.sns.Topic("alarm_actions_topic", {
  tags: {
    GLOBAL_KLOTHO_TAG: "stacksnap-dev",
    RESOURCE_NAME: "alarm_actions_topic",
  },
});
const vpc_0 = new aws.ec2.Vpc("vpc-0", {
  cidrBlock: "10.0.0.0/16",
  enableDnsHostnames: true,
  enableDnsSupport: true,
  tags: { GLOBAL_KLOTHO_TAG: "stacksnap-dev", RESOURCE_NAME: "vpc-0" },
});
const ecr_image_alarm_reporter = (() => {
  const pullBaseImage = new command.local.Command(
    `${"alarm_reporter"}-pull-base-image-${Date.now()}`,
    {
      create: pulumi.interpolate`docker pull ${"public.ecr.aws/lambda/python:3.12"} --platform ${"linux/amd64"}`,
    },
  );
  const base = new docker.Image(
    `${"alarm_reporter"}-base`,
    {
      build: {
        context: "..",
        dockerfile: "Dockerfile.AlarmReporter",
        platform: "linux/amd64",
      },
      skipPush: true,
      imageName: pulumi.interpolate`${alarm_reporter_ecr_repo.repositoryUrl}:base`,
    },
    {
      dependsOn: pullBaseImage,
    },
  );

  const sha256 = new command.local.Command(
    `${"alarm_reporter"}-base-get-sha256-${Date.now()}`,
    {
      create: pulumi.interpolate`docker image inspect -f {{.ID}} ${base.imageName}`,
    },
    { parent: base },
  ).stdout.apply((id) => id.substring(7));

  return new docker.Image(
    "alarm_reporter",
    {
      build: {
        context: "..",
        dockerfile: "Dockerfile.AlarmReporter",
        platform: "linux/amd64",
      },
      registry: aws.ecr
        .getAuthorizationTokenOutput(
          { registryId: alarm_reporter_ecr_repo.registryId },
          { async: true },
        )
        .apply((registryToken) => {
          return {
            server: alarm_reporter_ecr_repo.repositoryUrl,
            username: registryToken.userName,
            password: registryToken.password,
          };
        }),
      imageName: pulumi.interpolate`${alarm_reporter_ecr_repo.repositoryUrl}:${sha256}`,
    },
    { parent: base },
  );
})();
const stacksnap_task_image = (() => {
  const pullBaseImage = new command.local.Command(
    `${"stacksnap-task-image"}-pull-base-image-${Date.now()}`,
    {
      create: pulumi.interpolate`docker pull ${"python:3.11-slim-bookworm"} --platform ${"linux/amd64"}`,
    },
  );
  const base = new docker.Image(
    `${"stacksnap-task-image"}-base`,
    {
      build: {
        context: "..",
        dockerfile: "Dockerfile",
        platform: "linux/amd64",
      },
      skipPush: true,
      imageName: pulumi.interpolate`${stacksnap_task_image_ecr_repo.repositoryUrl}:base`,
    },
    {
      dependsOn: pullBaseImage,
    },
  );

  const sha256 = new command.local.Command(
    `${"stacksnap-task-image"}-base-get-sha256-${Date.now()}`,
    {
      create: pulumi.interpolate`docker image inspect -f {{.ID}} ${base.imageName}`,
    },
    { parent: base },
  ).stdout.apply((id) => id.substring(7));

  return new docker.Image(
    "stacksnap-task-image",
    {
      build: {
        context: "..",
        dockerfile: "Dockerfile",
        platform: "linux/amd64",
      },
      registry: aws.ecr
        .getAuthorizationTokenOutput(
          { registryId: stacksnap_task_image_ecr_repo.registryId },
          { async: true },
        )
        .apply((registryToken) => {
          return {
            server: stacksnap_task_image_ecr_repo.repositoryUrl,
            username: registryToken.userName,
            password: registryToken.password,
          };
        }),
      imageName: pulumi.interpolate`${stacksnap_task_image_ecr_repo.repositoryUrl}:${sha256}`,
    },
    { parent: base },
  );
})();
const stacksnap_ecs_launch_template_iam_instance_profile =
  new aws.iam.InstanceProfile(
    "stacksnap-ecs-launch-template-iam_instance_profile",
    {
      role: stacksnap_ecs_launch_template_iam_instance_profb0be8bf5,
      tags: {
        GLOBAL_KLOTHO_TAG: "stacksnap-dev",
        RESOURCE_NAME: "stacksnap-ecs-launch-template-iam_instance_profile",
      },
    },
  );
const alarm_reporter_executionrole = new aws.iam.Role(
  "alarm_reporter-ExecutionRole",
  {
    assumeRolePolicy: pulumi.jsonStringify({
      Statement: [
        {
          Action: ["sts:AssumeRole"],
          Effect: "Allow",
          Principal: { Service: ["lambda.amazonaws.com"] },
        },
      ],
      Version: "2012-10-17",
    }),
    managedPolicyArns: [
      ...["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
    ],
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "alarm_reporter-ExecutionRole",
    },
  },
);
const availability_zone_0 = pulumi.output(
  aws.getAvailabilityZones({
    state: "available",
  }),
).names[0];
const availability_zone_1 = pulumi.output(
  aws.getAvailabilityZones({
    state: "available",
  }),
).names[1];
const s3_bucket_policy_0 = new aws.s3.BucketPolicy("s3_bucket_policy-0", {
  bucket: stacksnap_ui.id,
  policy: {
    Statement: [
      {
        Action: ["s3:GetObject"],
        Effect: "Allow",
        Principal: { AWS: [cloudfront_origin_access_identity_0.iamArn] },
        Resource: [pulumi.interpolate`${stacksnap_ui.arn}/*`],
      },
    ],
    Version: "2012-10-17",
  },
});
const internet_gateway_0 = new aws.ec2.InternetGateway("internet_gateway-0", {
  vpcId: vpc_0.id,
  tags: {
    GLOBAL_KLOTHO_TAG: "stacksnap-dev",
    RESOURCE_NAME: "internet_gateway-0",
  },
});
const stacksnap_alb_security_group = new aws.ec2.SecurityGroup(
  "stacksnap-alb-security_group",
  {
    name: "stacksnap-alb-security_group",
    vpcId: vpc_0.id,
    egress: [
      {
        cidrBlocks: ["0.0.0.0/0"],
        description: "Allows all outbound IPv4 traffic",
        fromPort: 0,
        protocol: "-1",
        toPort: 0,
      },
    ],
    ingress: [
      {
        cidrBlocks: ["0.0.0.0/0"],
        description:
          "Allow ingress traffic from within the same security group",
        fromPort: 0,
        protocol: "-1",
        toPort: 0,
      },
      {
        description:
          "Allow ingress traffic from within the same security group",
        fromPort: 0,
        protocol: "-1",
        self: true,
        toPort: 0,
      },
    ],
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-alb-security_group",
    },
  },
);
const stacksnap_service_security_group = new aws.ec2.SecurityGroup(
  "stacksnap-service-security_group",
  {
    name: "stacksnap-service-security_group",
    vpcId: vpc_0.id,
    egress: [
      {
        cidrBlocks: ["0.0.0.0/0"],
        description: "Allows all outbound IPv4 traffic",
        fromPort: 0,
        protocol: "-1",
        toPort: 0,
      },
    ],
    ingress: [
      {
        cidrBlocks: ["10.0.0.0/18"],
        description:
          "Allow ingress traffic from ip addresses within the subnet subnet-2",
        fromPort: 0,
        protocol: "-1",
        toPort: 0,
      },
      {
        cidrBlocks: ["10.0.128.0/18"],
        description:
          "Allow ingress traffic from ip addresses within the subnet subnet-1",
        fromPort: 0,
        protocol: "-1",
        toPort: 0,
      },
      {
        cidrBlocks: ["10.0.192.0/18"],
        description:
          "Allow ingress traffic from ip addresses within the subnet subnet-0",
        fromPort: 0,
        protocol: "-1",
        toPort: 0,
      },
      {
        cidrBlocks: ["10.0.64.0/18"],
        description:
          "Allow ingress traffic from ip addresses within the subnet subnet-3",
        fromPort: 0,
        protocol: "-1",
        toPort: 0,
      },
      {
        description:
          "Allow ingress traffic from within the same security group",
        fromPort: 0,
        protocol: "-1",
        self: true,
        toPort: 0,
      },
    ],
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-service-security_group",
    },
  },
);
const stacksnap_tg = (() => {
  const tg = new aws.lb.TargetGroup("stacksnap-tg", {
    port: 80,
    protocol: "HTTP",
    targetType: "ip",
    vpcId: vpc_0.id,
    healthCheck: {
      enabled: true,
      healthyThreshold: 5,
      interval: 30,
      matcher: "200-299",
      path: "/api/ping",
      protocol: "HTTP",
      timeout: 5,
      unhealthyThreshold: 2,
    },
    tags: { GLOBAL_KLOTHO_TAG: "stacksnap-dev", RESOURCE_NAME: "stacksnap-tg" },
  });
  return tg;
})();
const stacksnap_ecs_launch_template = new aws.ec2.LaunchTemplate(
  "stacksnap-ecs-launch-template",
  {
    iamInstanceProfile: {
      arn: stacksnap_ecs_launch_template_iam_instance_profile.arn,
    },
    imageId: aws.ec2
      .getAmi({
        filters: [
          {
            name: "name",
            values: ["amzn2-ami-ecs-hvm-*-x86_64-ebs"],
          },
        ],
        owners: ["amazon"], // AWS account ID for Amazon AMIs
        mostRecent: true,
      })
      .then((ami) => ami.id),
    instanceType: "t3.large",
    userData: pulumi.interpolate`#!/bin/bash
echo ECS_CLUSTER=${stacksnap_ecs_cluster.name} >> /etc/ecs/ecs.config
`.apply((userData) => Buffer.from(userData).toString("base64")),
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-ecs-launch-template",
    },
  },
);

const stacksnap_shared_storage = new aws.efs.FileSystem(
  "stacksnap-shared-storage",
  {
    encrypted: true,
    performanceMode: "generalPurpose",
    throughputMode: "bursting",
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-shared-storage",
    },
  },
  {
    dependsOn: [],
  },
);
const subnet_2_route_table = new aws.ec2.RouteTable("subnet-2-route_table", {
  vpcId: vpc_0.id,
  routes: [
    {
      cidrBlock: "0.0.0.0/0",
      gatewayId: internet_gateway_0.id,
    },
  ],

  tags: {
    GLOBAL_KLOTHO_TAG: "stacksnap-dev",
    RESOURCE_NAME: "subnet-2-route_table",
  },
});
const subnet_3_route_table = new aws.ec2.RouteTable("subnet-3-route_table", {
  vpcId: vpc_0.id,
  routes: [
    {
      cidrBlock: "0.0.0.0/0",
      gatewayId: internet_gateway_0.id,
    },
  ],

  tags: {
    GLOBAL_KLOTHO_TAG: "stacksnap-dev",
    RESOURCE_NAME: "subnet-3-route_table",
  },
});

const stacksnap_service_stacksnap_shared_storage = new aws.efs.AccessPoint(
  "stacksnap-service-stacksnap-shared-storage",
  {
    fileSystemId: stacksnap_shared_storage.id,
    posixUser: { gid: 1000, uid: 1000 },
    rootDirectory: {
      creationInfo: { ownerGid: 1000, ownerUid: 1000, permissions: "777" },
      path: "/mnt/efs",
    },
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-service-stacksnap-shared-storage",
    },
  },
);
const stacksnap_ecs_task_role = new aws.iam.Role("stacksnap-ecs-task-role", {
  assumeRolePolicy: pulumi.jsonStringify({
    Statement: [
      {
        Action: ["sts:AssumeRole"],
        Effect: "Allow",
        Principal: { Service: ["ecs-tasks.amazonaws.com"] },
      },
    ],
    Version: "2012-10-17",
  }),
  inlinePolicies: [
    {
      name: "allow-sts-assume-role",
      policy: pulumi.jsonStringify({
        Statement: [
          { Action: ["sts:AssumeRole"], Effect: "Allow", Resource: ["*"] },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "project-applications-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: ["dynamodb:*"],
            Effect: "Allow",
            Resource: [
              project_applications.arn,
              pulumi.interpolate`${project_applications.arn}/stream/*`,
              pulumi.interpolate`${project_applications.arn}/backup/*`,
              pulumi.interpolate`${project_applications.arn}/export/*`,
              pulumi.interpolate`${project_applications.arn}/index/*`,
            ],
          },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "projects-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: ["dynamodb:*"],
            Effect: "Allow",
            Resource: [
              projects.arn,
              pulumi.interpolate`${projects.arn}/stream/*`,
              pulumi.interpolate`${projects.arn}/backup/*`,
              pulumi.interpolate`${projects.arn}/export/*`,
              pulumi.interpolate`${projects.arn}/index/*`,
            ],
          },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "pulumi-stacks-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: ["dynamodb:*"],
            Effect: "Allow",
            Resource: [
              pulumi_stacks.arn,
              pulumi.interpolate`${pulumi_stacks.arn}/stream/*`,
              pulumi.interpolate`${pulumi_stacks.arn}/backup/*`,
              pulumi.interpolate`${pulumi_stacks.arn}/export/*`,
              pulumi.interpolate`${pulumi_stacks.arn}/index/*`,
            ],
          },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "workflow-jobs-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: ["dynamodb:*"],
            Effect: "Allow",
            Resource: [
              workflow_jobs.arn,
              pulumi.interpolate`${workflow_jobs.arn}/stream/*`,
              pulumi.interpolate`${workflow_jobs.arn}/backup/*`,
              pulumi.interpolate`${workflow_jobs.arn}/export/*`,
              pulumi.interpolate`${workflow_jobs.arn}/index/*`,
            ],
          },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "workflow-runs-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: ["dynamodb:*"],
            Effect: "Allow",
            Resource: [
              workflow_runs.arn,
              pulumi.interpolate`${workflow_runs.arn}/stream/*`,
              pulumi.interpolate`${workflow_runs.arn}/backup/*`,
              pulumi.interpolate`${workflow_runs.arn}/export/*`,
              pulumi.interpolate`${workflow_runs.arn}/index/*`,
            ],
          },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "stacksnap-shared-storage-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: ["elasticfilesystem:Client*"],
            Effect: "Allow",
            Resource: [stacksnap_shared_storage.arn],
          },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "stacksnap-binaries-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: ["s3:*"],
            Effect: "Allow",
            Resource: [
              stacksnap_binaries.arn,
              pulumi.interpolate`${stacksnap_binaries.arn}/*`,
            ],
          },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "stacksnap-iac-store-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: ["s3:*"],
            Effect: "Allow",
            Resource: [
              stacksnap_iac_store.arn,
              pulumi.interpolate`${stacksnap_iac_store.arn}/*`,
            ],
          },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "stacksnap-pulumi-state-bucket-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: ["s3:*"],
            Effect: "Allow",
            Resource: [
              stacksnap_pulumi_state_bucket.arn,
              pulumi.interpolate`${stacksnap_pulumi_state_bucket.arn}/*`,
            ],
          },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "stacksnap-pulumi-access-token-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: [
              "secretsmanager:DescribeSecret",
              "secretsmanager:GetSecretValue",
            ],
            Effect: "Allow",
            Resource: [stacksnap_pulumi_access_token.arn],
          },
        ],
        Version: "2012-10-17",
      }),
    },
    {
      name: "stacksnap-email-identity-policy",
      policy: pulumi.jsonStringify({
        Statement: [
          {
            Action: ["ses:SendEmail", "ses:SendRawEmail"],
            Effect: "Allow",
            Resource: ["*"],
          },
        ],
        Version: "2012-10-17",
      }),
    },
  ],
  managedPolicyArns: [
    ...[
      "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
    ],
  ],
  tags: {
    GLOBAL_KLOTHO_TAG: "stacksnap-dev",
    RESOURCE_NAME: "stacksnap-ecs-task-role",
  },
});
const subnet_2 = new aws.ec2.Subnet("subnet-2", {
  vpcId: vpc_0.id,
  cidrBlock: "10.0.0.0/18",
  availabilityZone: availability_zone_0,
  mapPublicIpOnLaunch: false,
  tags: { GLOBAL_KLOTHO_TAG: "stacksnap-dev", RESOURCE_NAME: "subnet-2" },
});
const subnet_3 = new aws.ec2.Subnet("subnet-3", {
  vpcId: vpc_0.id,
  cidrBlock: "10.0.64.0/18",
  availabilityZone: availability_zone_1,
  mapPublicIpOnLaunch: false,
  tags: { GLOBAL_KLOTHO_TAG: "stacksnap-dev", RESOURCE_NAME: "subnet-3" },
});
const stacksnap_task = new aws.ecs.TaskDefinition("stacksnap-task", {
  family: "stacksnap-task",
  cpu: "2048",
  memory: "3200",
  networkMode: "awsvpc",
  executionRoleArn: stacksnap_ecs_task_role.arn,
  taskRoleArn: stacksnap_ecs_task_role.arn,
  volumes: [
    {
      name: "stacksnap-service-stacksnap-shared-storage",
      efsVolumeConfiguration: {
        fileSystemId: stacksnap_shared_storage.id,
        authorizationConfig: {
          accessPointId: stacksnap_service_stacksnap_shared_storage.id,
          iam: "ENABLED",
        },
        transitEncryption: "ENABLED",
      },
    },
    {
      name: "docker_sock",
      hostPath: "/var/run/docker.sock",
    },
  ],
  containerDefinitions: pulumi.jsonStringify([
    {
      cpu: 2048,
      environment: [
        {
          name: "PULUMISTACKS_TABLE_NAME",
          value: pulumi_stacks.name,
        },
        {
          name: "PROJECTS_TABLE_NAME",
          value: projects.name,
        },
        {
          name: "APP_DEPLOYMENTS_TABLE_NAME",
          value: project_applications.name,
        },
        {
          name: "WORKFLOW_RUNS_TABLE_NAME",
          value: workflow_runs.name,
        },
        {
          name: "WORKFLOW_JOBS_TABLE_NAME",
          value: workflow_jobs.name,
        },
        {
          name: "IAC_STORE_BUCKET_NAME",
          value: stacksnap_iac_store.bucket,
        },
        {
          name: "STACK_SNAP_BINARIES_BUCKET_NAME",
          value: stacksnap_binaries.bucket,
        },
        {
          name: "AUTH0_DOMAIN",
          value: kloConfig.require("AuthDomain"),
        },
        {
          name: "AUTH0_AUDIENCE",
          value: kloConfig.require("AuthAudience"),
        },
        {
          name: "PULUMI_ACCESS_TOKEN_ID",
          value: stacksnap_pulumi_access_token.id,
        },
        {
          name: "SES_SENDER_ADDRESS",
          value: "stacksnap@klo.dev",
        },
        {
          name: "DEPLOY_LOG_DIR",
          value: "/app/deployments",
        },
        {
          name: "PULUMI_STATE_BUCKET_NAME",
          value: stacksnap_pulumi_state_bucket.bucket,
        },
        {
          name: "PROJECT_APPLICATIONS_TABLE_NAME",
          value: project_applications.name,
        },
        {
          name: "PULUMI_STACKS_TABLE_NAME",
          value: pulumi_stacks.name,
        },
        {
          name: "STACKSNAP_BINARIES_BUCKET_NAME",
          value: stacksnap_binaries.bucket,
        },
        {
          name: "STACKSNAP_IAC_STORE_BUCKET_NAME",
          value: stacksnap_iac_store.bucket,
        },
        {
          name: "STACKSNAP_PULUMI_STATE_BUCKET_BUCKET_NAME",
          value: stacksnap_pulumi_state_bucket.bucket,
        },
        {
          name: "STACKSNAP_PULUMI_ACCESS_TOKEN_ID",
          value: stacksnap_pulumi_access_token.id,
        },
      ],
      essential: true,
      healthCheck: {
        command: [
          "CMD-SHELL",
          "curl -f http://localhost:80/api/ping || exit 1",
        ],
      },
      image: stacksnap_task_image.imageName,
      logConfiguration: {
        logDriver: "awslogs",
        options: {
          "awslogs-group": "/aws/ecs/stacksnap-task",
          "awslogs-region": region_0.apply((o) => o.name),
          "awslogs-stream-prefix": "stacksnap-task-stacksnap-backend",
        },
      },
      memory: 3200,
      mountPoints: [
        {
          containerPath: "/app/deployments",
          sourceVolume: "stacksnap-service-stacksnap-shared-storage",
        },
        {
          containerPath: "/var/run/docker.sock",
          sourceVolume: "docker_sock",
        },
      ],
      name: "stacksnap-backend",
      portMappings: [
        {
          containerPort: 80,
          hostPort: 80,
          protocol: "TCP",
        },
      ],
    },
  ]),
  tags: { GLOBAL_KLOTHO_TAG: "stacksnap-dev", RESOURCE_NAME: "stacksnap-task" },
});
const subnet_0_route_table_nat_gateway = new aws.ec2.NatGateway(
  "subnet-0-route_table-nat_gateway",
  {
    allocationId: subnet_0_route_table_nat_gateway_elastic_ip.id,
    subnetId: subnet_2.id,
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "subnet-0-route_table-nat_gateway",
    },
  },
);
const subnet_2_subnet_2_route_table = new aws.ec2.RouteTableAssociation(
  "subnet-2-subnet-2-route_table",
  {
    subnetId: subnet_2.id,
    routeTableId: subnet_2_route_table.id,
  },
);
const stacksnap_alb = new aws.lb.LoadBalancer("stacksnap-alb", {
  internal: false,
  loadBalancerType: "application",
  subnets: [subnet_2, subnet_3].map((subnet) => subnet.id),
  tags: { GLOBAL_KLOTHO_TAG: "stacksnap-dev", RESOURCE_NAME: "stacksnap-alb" },
  securityGroups: [stacksnap_alb_security_group].map((sg) => sg.id),
});
export const stacksnap_alb_DomainName = stacksnap_alb.dnsName;
const subnet_1_route_table_nat_gateway = new aws.ec2.NatGateway(
  "subnet-1-route_table-nat_gateway",
  {
    allocationId: subnet_1_route_table_nat_gateway_elastic_ip.id,
    subnetId: subnet_3.id,
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "subnet-1-route_table-nat_gateway",
    },
  },
);
const subnet_3_subnet_3_route_table = new aws.ec2.RouteTableAssociation(
  "subnet-3-subnet-3-route_table",
  {
    subnetId: subnet_3.id,
    routeTableId: subnet_3_route_table.id,
  },
);
const subnet_0_route_table = new aws.ec2.RouteTable("subnet-0-route_table", {
  vpcId: vpc_0.id,
  routes: [
    {
      cidrBlock: "0.0.0.0/0",
      natGatewayId: subnet_0_route_table_nat_gateway.id,
    },
  ],

  tags: {
    GLOBAL_KLOTHO_TAG: "stacksnap-dev",
    RESOURCE_NAME: "subnet-0-route_table",
  },
});
const stacksnap_distribution = new aws.cloudfront.Distribution(
  "stacksnap-distribution",
  {
    origins: [
      {
        customOriginConfig: {
          httpPort: 80,
          httpsPort: 443,
          originProtocolPolicy: "http-only",
          originSslProtocols: ["TLSv1.2", "TLSv1", "SSLv3", "TLSv1.1"],
        },
        domainName: stacksnap_alb.dnsName,
        originId: "stacksnap-alb",
      },
      {
        domainName: stacksnap_ui.bucketRegionalDomainName,
        originId: "stacksnap-ui",
        s3OriginConfig: {
          originAccessIdentity:
            cloudfront_origin_access_identity_0.cloudfrontAccessIdentityPath,
        },
      },
    ],
    enabled: true,
    viewerCertificate: {
      acmCertificateArn: kloConfig.require("CertificateArn"),
      sslSupportMethod: "sni-only",
    },
    orderedCacheBehaviors: [
      {
        allowedMethods: [
          "DELETE",
          "GET",
          "HEAD",
          "OPTIONS",
          "PATCH",
          "POST",
          "PUT",
        ],
        cachePolicyId: "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
        cachedMethods: ["GET", "HEAD"],
        defaultTtl: 0,
        maxTtl: 0,
        minTtl: 0,
        originRequestPolicyId: "b689b0a8-53d0-40ab-baf2-68738e2966ac",
        pathPattern: "/api/*",
        smoothStreaming: false,
        targetOriginId: "stacksnap-alb",
        viewerProtocolPolicy: "redirect-to-https",
      },
    ],
    aliases: [kloConfig.require("Alias")],
    customErrorResponses: [
      { errorCode: 403, responseCode: 200, responsePagePath: "/index.html" },
    ],
    defaultCacheBehavior: {
      allowedMethods: [
        "DELETE",
        "GET",
        "HEAD",
        "OPTIONS",
        "PATCH",
        "POST",
        "PUT",
      ],
      cachePolicyId: "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
      cachedMethods: ["HEAD", "GET"],
      defaultTtl: 3600,
      maxTtl: 86400,
      minTtl: 0,
      originRequestPolicyId: "b689b0a8-53d0-40ab-baf2-68738e2966ac",
      targetOriginId: "stacksnap-ui",
      viewerProtocolPolicy: "allow-all",
    },
    restrictions: { geoRestriction: { restrictionType: "none" } },
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-distribution",
    },
  },
);
export const stacksnap_distribution_Domain = stacksnap_distribution.domainName;
const stacksnap_alb_listener = new aws.lb.Listener("stacksnap-alb-listener", {
  loadBalancerArn: stacksnap_alb.arn,
  defaultActions: [
    {
      targetGroupArn: stacksnap_tg.arn,
      type: "forward",
    },
  ],

  port: 80,
  protocol: "HTTP",
  tags: {
    GLOBAL_KLOTHO_TAG: "stacksnap-dev",
    RESOURCE_NAME: "stacksnap-alb-listener",
  },
});
const subnet_1_route_table = new aws.ec2.RouteTable("subnet-1-route_table", {
  vpcId: vpc_0.id,
  routes: [
    {
      cidrBlock: "0.0.0.0/0",
      natGatewayId: subnet_1_route_table_nat_gateway.id,
    },
  ],

  tags: {
    GLOBAL_KLOTHO_TAG: "stacksnap-dev",
    RESOURCE_NAME: "subnet-1-route_table",
  },
});
const subnet_0 = new aws.ec2.Subnet("subnet-0", {
  vpcId: vpc_0.id,
  cidrBlock: "10.0.192.0/18",
  availabilityZone: availability_zone_1,
  mapPublicIpOnLaunch: false,
  tags: { GLOBAL_KLOTHO_TAG: "stacksnap-dev", RESOURCE_NAME: "subnet-0" },
});
const stacksnap_alb_listener_rule = new aws.lb.ListenerRule(
  "stacksnap-alb-listener-rule",
  {
    listenerArn: stacksnap_alb_listener.arn,
    priority: 1,
    conditions: [{ pathPattern: { values: ["/api/*"] } }],
    actions: [
      {
        type: "forward",
        targetGroupArn: stacksnap_tg.arn,
      },
    ],

    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-alb-listener-rule",
    },
  },
);
const subnet_1 = new aws.ec2.Subnet("subnet-1", {
  vpcId: vpc_0.id,
  cidrBlock: "10.0.128.0/18",
  availabilityZone: availability_zone_0,
  mapPublicIpOnLaunch: false,
  tags: { GLOBAL_KLOTHO_TAG: "stacksnap-dev", RESOURCE_NAME: "subnet-1" },
});
const subnet_0_stacksnap_shared_storage = new aws.efs.MountTarget(
  "subnet-0-stacksnap-shared-storage",
  {
    fileSystemId: stacksnap_shared_storage.id,
    subnetId: subnet_0.id,
    securityGroups: [stacksnap_service_security_group]?.map((sg) => sg.id),
  },
);
const subnet_0_subnet_0_route_table = new aws.ec2.RouteTableAssociation(
  "subnet-0-subnet-0-route_table",
  {
    subnetId: subnet_0.id,
    routeTableId: subnet_0_route_table.id,
  },
);
const stacksnap_asg = new aws.autoscaling.Group("stacksnap-asg", {
  defaultCooldown: 300,
  launchTemplate: {
    id: stacksnap_ecs_launch_template.id,
    version: "$Latest",
  },
  tags: [
    {
      key: "GLOBAL_KLOTHO_TAG",
      value: "stacksnap-dev",
      propagateAtLaunch: true,
    },
    {
      key: "RESOURCE_NAME",
      value: "stacksnap-asg",
      propagateAtLaunch: true,
    },
  ],
  maxSize: 2,
  minSize: 1,
  vpcZoneIdentifiers: [subnet_0.id, subnet_1.id],
});
const subnet_1_stacksnap_shared_storage = new aws.efs.MountTarget(
  "subnet-1-stacksnap-shared-storage",
  {
    fileSystemId: stacksnap_shared_storage.id,
    subnetId: subnet_1.id,
    securityGroups: [stacksnap_service_security_group]?.map((sg) => sg.id),
  },
);
const subnet_1_subnet_1_route_table = new aws.ec2.RouteTableAssociation(
  "subnet-1-subnet-1-route_table",
  {
    subnetId: subnet_1.id,
    routeTableId: subnet_1_route_table.id,
  },
);
const stacksnap_capacity_provider = new aws.ecs.CapacityProvider(
  "stacksnap-capacity-provider",
  {
    autoScalingGroupProvider: {
      autoScalingGroupArn: stacksnap_asg.arn,
      managedScaling: {
        instanceWarmupPeriod: 300,
        maximumScalingStepSize: 10000,
        minimumScalingStepSize: 1,
        status: "ENABLED",
        targetCapacity: 100,
      },
    },
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-capacity-provider",
    },
  },
);
const stacksnap_cluster_capacity_provider =
  new aws.ecs.ClusterCapacityProviders("stacksnap-cluster-capacity-provider", {
    clusterName: stacksnap_ecs_cluster.name,
    capacityProviders: [stacksnap_capacity_provider.name],
    defaultCapacityProviderStrategies: [
      {
        base: 0,
        capacityProvider: stacksnap_capacity_provider.name,
        weight: 0,
      },
    ],
  });
const stacksnap_service = new aws.ecs.Service(
  "stacksnap-service",
  {
    capacityProviderStrategies: [
      { capacityProvider: stacksnap_capacity_provider.name, weight: 1 },
    ],
    cluster: stacksnap_ecs_cluster.arn,
    desiredCount: 1,
    forceNewDeployment: true,
    loadBalancers: [
      {
        containerPort: 80,
        targetGroupArn: stacksnap_tg.arn,
        containerName: "stacksnap-backend",
      },
    ],

    networkConfiguration: {
      subnets: [subnet_0, subnet_1].map((sn) => sn.id),
      securityGroups: [stacksnap_service_security_group].map((sg) => sg.id),
    },
    taskDefinition: stacksnap_task.arn,
    waitForSteadyState: true,
    //TMP
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-service",
    },
  },
  {
    dependsOn: [
      stacksnap_capacity_provider,
      stacksnap_ecs_cluster,
      stacksnap_service_security_group,
      stacksnap_task,
      stacksnap_tg,
      subnet_0,
      subnet_1,
    ],
  },
);
const stacksnap_service_cpuutilization = new aws.cloudwatch.MetricAlarm(
  "stacksnap-service-CPUUtilization",
  {
    comparisonOperator: "GreaterThanOrEqualToThreshold",
    evaluationPeriods: 2,
    actionsEnabled: true,
    alarmActions: [alarm_actions_topic.arn],
    alarmDescription:
      "This metric checks for CPUUtilization in the ECS service",
    dimensions: {
      ClusterName: stacksnap_ecs_cluster.name,
      ServiceName: stacksnap_service.name,
    },
    insufficientDataActions: [alarm_actions_topic.arn],
    metricName: "CPUUtilization",
    namespace: "AWS/ECS",
    okActions: [alarm_actions_topic.arn],
    period: 60,
    statistic: "Average",
    threshold: 90,
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-service-CPUUtilization",
    },
  },
);
const stacksnap_service_memoryutilization = new aws.cloudwatch.MetricAlarm(
  "stacksnap-service-MemoryUtilization",
  {
    comparisonOperator: "GreaterThanOrEqualToThreshold",
    evaluationPeriods: 2,
    actionsEnabled: true,
    alarmActions: [alarm_actions_topic.arn],
    alarmDescription:
      "This metric checks for MemoryUtilization in the ECS service",
    dimensions: {
      ClusterName: stacksnap_ecs_cluster.name,
      ServiceName: stacksnap_service.name,
    },
    insufficientDataActions: [alarm_actions_topic.arn],
    metricName: "MemoryUtilization",
    namespace: "AWS/ECS",
    okActions: [alarm_actions_topic.arn],
    period: 60,
    statistic: "Average",
    threshold: 90,
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-service-MemoryUtilization",
    },
  },
);
const stacksnap_service_runningtaskcount = new aws.cloudwatch.MetricAlarm(
  "stacksnap-service-RunningTaskCount",
  {
    comparisonOperator: "LessThanThreshold",
    evaluationPeriods: 1,
    actionsEnabled: true,
    alarmActions: [alarm_actions_topic.arn],
    alarmDescription:
      "This metric checks for any stopped tasks in the ECS service",
    dimensions: {
      ClusterName: stacksnap_ecs_cluster.name,
      ServiceName: stacksnap_service.name,
    },
    insufficientDataActions: [alarm_actions_topic.arn],
    metricName: "RunningTaskCount",
    namespace: "ECS/ContainerInsights",
    okActions: [alarm_actions_topic.arn],
    period: 60,
    statistic: "Average",
    threshold: 1,
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "stacksnap-service-RunningTaskCount",
    },
  },
);
const albAlarms = createALBAlarms(stacksnap_alb, alarm_actions_topic);
const customAlarms = createCustomAlarms(
  stacksnap_task_log_group,
  alarm_actions_topic,
);

const cloudwatch_dashboard_0 = new aws.cloudwatch.Dashboard(
  "cloudwatch_dashboard-0",
  {
    dashboardName: "cloudwatch_dashboard-0",
    dashboardBody: pulumi.jsonStringify({
      widgets: [
        {
          height: 6,
          properties: {
            annotations: { alarms: [stacksnap_service_cpuutilization.arn] },
            region: region_0.apply((o) => o.name),
          },
          type: "metric",
          width: 6,
        },
        {
          height: 6,
          properties: {
            annotations: { alarms: [stacksnap_service_memoryutilization.arn] },
            region: region_0.apply((o) => o.name),
          },
          type: "metric",
          width: 6,
        },
        {
          height: 6,
          properties: {
            annotations: { alarms: [stacksnap_service_runningtaskcount.arn] },
            region: region_0.apply((o) => o.name),
          },
          type: "metric",
          width: 6,
        },
        {
          height: 6,
          properties: {
            annotations: { alarms: albAlarms.map((a) => a.arn) },
            region: region_0.apply((o) => o.name),
          },
          type: "metric",
          width: 6,
        },
        {
          height: 6,
          properties: {
            annotations: { alarms: customAlarms.map((a) => a.arn) },
            region: region_0.apply((o) => o.name),
          },
          type: "metric",
          width: 6,
        },
      ],
    }),
  },
);

const lambda_function_alarm_reporter = new aws.lambda.Function(
  "alarm_reporter",
  {
    packageType: "Image",
    imageUri: ecr_image_alarm_reporter.imageName,
    memorySize: 512,
    timeout: 180,
    role: alarm_reporter_executionrole.arn,
    name: "alarm_reporter",
    environment: {
      variables: {
        ALARM_STATE_ONLY_ALARMS: pulumi.jsonStringify(customAlarms.map((a) => a.name)),
      },
    },
    tags: {
      GLOBAL_KLOTHO_TAG: "stacksnap-dev",
      RESOURCE_NAME: "alarm_reporter",
    },
  },
  {
    dependsOn: [
      alarm_reporter_executionrole,
      alarm_reporter_log_group,
      ecr_image_alarm_reporter,
    ],
  },
);

const lambda_permission_alarm_actions_topic_alarm_reporter =
  new aws.lambda.Permission("alarm_actions_topic-alarm_reporter", {
    action: "lambda:InvokeFunction",
    function: lambda_function_alarm_reporter.name,
    principal: "sns.amazonaws.com",
    sourceArn: alarm_actions_topic.arn,
  });
const sns_topic_subscription_alarm_actions_topic_alarm_reporter =
  new aws.sns.TopicSubscription("alarm_actions_topic-alarm_reporter", {
    endpoint: lambda_function_alarm_reporter.arn,
    protocol: "lambda",
    topic: alarm_actions_topic.arn,
  });