import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";
import * as arnParser from "@aws-sdk/util-arn-parser";

export function CreateDeploymentStateMachine(
  namePrefix: string,
  cluster: aws.ecs.Cluster,
  deployApp: aws.ecs.TaskDefinition,
  succeedRun: aws.ecs.TaskDefinition,
  failRun: aws.ecs.TaskDefinition,
  subnets: aws.ec2.Subnet[],
  securityGroups: aws.ec2.SecurityGroup[]
): aws.sfn.StateMachine {
  const deployRole = new aws.iam.Role("deployRole", {
    namePrefix,
    assumeRolePolicy: JSON.stringify({
      Version: "2012-10-17",
      Statement: [
        {
          Action: "sts:AssumeRole",
          Effect: "Allow",
          Principal: {
            Service: "states.amazonaws.com",
          },
        },
      ],
    }),
  });
  const ecsTaskPolicy = new aws.iam.RolePolicy("deployEcsTaskPolicy", {
    role: deployRole,
    name: "EcsTaskManagementScopedAccessPolicy",
    policy: pulumi.jsonStringify({
      Version: "2012-10-17",
      Statement: [
        {
          Action: ["ecs:RunTask", "ecs:StopTask", "ecs:DescribeTasks"],
          Effect: "Allow",
          Resource: [...new Set([deployApp.arn, succeedRun.arn, failRun.arn])],
        },
        {
          Action: ["iam:PassRole"],
          Effect: "Allow",
          Resource: [
            ...new Set([
              deployApp.taskRoleArn,
              succeedRun.taskRoleArn,
              failRun.taskRoleArn,
              deployApp.executionRoleArn,
              succeedRun.executionRoleArn,
              failRun.executionRoleArn,
            ]),
          ],
        },
        {
          Action: [
            "events:PutTargets",
            "events:PutRule",
            "events:DescribeRule",
          ],
          Effect: "Allow",
          Resource: [
            // Copy the region and account from the clusterArn
            cluster.arn.apply((clusterArn) => {
              const parts = arnParser.parse(clusterArn);
              return arnParser.build({
                ...parts,
                service: "events",
                resource: "rule/StepFunctionsGetEventsForECSTaskRule",
              });
            }),
          ],
        },
      ],
    }),
  });
  const xrayPolicy = new aws.iam.RolePolicy("deployXRayPolicy", {
    role: deployRole,
    name: "XRayAccessPolicy",
    policy: pulumi.jsonStringify({
      Version: "2012-10-17",
      Statement: [
        {
          Action: [
            "xray:PutTraceSegments",
            "xray:PutTelemetryRecords",
            "xray:GetSamplingRules",
            "xray:GetSamplingTargets",
          ],
          Effect: "Allow",
          Resource: "*",
        },
      ],
    }),
  });
  const networkConfig = {
    AwsvpcConfiguration: {
      Subnets: subnets.map((subnet) => subnet.id),
      SecurityGroups: securityGroups.map((sg) => sg.id),
    },
  };

  // input:
  // {
  //   "projectId": "123",
  //   "runId": "123",
  //   "jobId": "123",
  //   "jobNumbers": {
  //     "common": "1",
  //     "apps": ["2", "3"]
  //    },
  // }
  const definition = pulumi.jsonStringify({
    StartAt: "Run Common",
    States: {
      "Run Common": {
        Type: "Task",
        Resource: "arn:aws:states:::ecs:runTask.sync",
        Parameters: {
          LaunchType: "FARGATE",
          Cluster: cluster.arn,
          TaskDefinition: deployApp.arn,
          NetworkConfiguration: networkConfig,
          Overrides: {
            ContainerOverrides: [
              {
                Name: "stacksnap-cli",
                "Command.$":
                  "States.Array('deploy', '--job-id', $.input.jobId, '--job-number', $.input.jobNumbers.common)",
              },
            ],
          },
        },
        Next: "Run all Apps",
        Catch: [
          {
            ErrorEquals: ["States.ALL"],
            Next: "Fail Run (common)",
            Comment: "on fail",
            ResultPath: "$.result",
          },
        ],
        ResultPath: "$.result",
      },
      "Fail Run (common)": {
        Type: "Task",
        Resource: "arn:aws:states:::ecs:runTask.sync",
        Parameters: {
          LaunchType: "FARGATE",
          Cluster: cluster.arn,
          TaskDefinition: failRun.arn,
          NetworkConfiguration: networkConfig,
          Overrides: {
            ContainerOverrides: [
              {
                Name: "stacksnap-cli",
                "Command.$":
                  "States.Array('abort-workflow', '--project-id', $.input.projectId, '--run-id', $.input.runId)",
              },
            ],
          },
        },
        Next: "Fail (common)",
      },
      "Fail (common)": {
        Type: "Fail",
      },
      "Run all Apps": {
        Type: "Map",
        ItemProcessor: {
          ProcessorConfig: {
            Mode: "INLINE",
          },
          StartAt: "Run App",
          States: {
            "Run App": {
              Type: "Task",
              Resource: "arn:aws:states:::ecs:runTask.sync",
              Parameters: {
                LaunchType: "FARGATE",
                Cluster: cluster.arn,
                TaskDefinition: deployApp.arn,
                NetworkConfiguration: networkConfig,
                Overrides: {
                  ContainerOverrides: [
                    {
                      Name: "stacksnap-cli",
                      "Command.$":
                        "States.Array('deploy', '--job-id', $.input.jobId, '--job-number', $.jobId)",
                    },
                  ],
                },
              },
              Catch: [
                {
                  ErrorEquals: ["States.ALL"],
                  Next: "Fail Run (app)",
                  ResultPath: "$.result",
                },
              ],
              End: true,
              ResultPath: "$.result",
            },
            "Fail Run (app)": {
              Type: "Task",
              Resource: "arn:aws:states:::ecs:runTask.sync",
              Parameters: {
                LaunchType: "FARGATE",
                Cluster: cluster.arn,
                TaskDefinition: failRun.arn,
                NetworkConfiguration: networkConfig,
                Overrides: {
                  ContainerOverrides: [
                    {
                      Name: "stacksnap-cli",
                      "Command.$":
                        "States.Array('abort-workflow', '--project-id', $.input.projectId, '--run-id', $.input.runId)",
                    },
                  ],
                },
              },
              Next: "Fail (app)",
            },
            "Fail (app)": {
              Type: "Fail",
            },
          },
        },
        Next: "Succeed Run",
        Label: "RunallApps",
        MaxConcurrency: 40,
        ItemSelector: {
          "input.$": "$.input",
          "jobId.$": "$$.Map.Item.Value",
        },
        ItemsPath: "$.input.jobNumbers.apps",
        ResultPath: "$.result",
      },
      "Succeed Run": {
        Type: "Task",
        Resource: "arn:aws:states:::ecs:runTask.sync",
        Parameters: {
          LaunchType: "FARGATE",
          Cluster: cluster.arn,
          TaskDefinition: succeedRun.arn,
          NetworkConfiguration: networkConfig,
          Overrides: {
            ContainerOverrides: [
              {
                Name: "stacksnap-cli",
                "Command.$":
                  "States.Array('complete-workflow', '--project-id', $.input.projectId, '--run-id', $.input.runId)",
              },
            ],
          },
        },
        Next: "Success",
      },
      Success: {
        Type: "Succeed",
      },
    },
    Comment: "Deploys a set of apps (including common)",
  });

  const stateMachine = new aws.sfn.StateMachine("deployment", {
    namePrefix: "stacksnap-deployer",
    definition,
    roleArn: deployRole.arn,
  });

  const redrivePolicy = new aws.iam.RolePolicy("deployRedrivePolicy", {
    role: deployRole,
    name: "StepFunctionsRedriveExecutionManagementScopedAccessPolicy",
    policy: pulumi.jsonStringify({
      Version: "2012-10-17",
      Statement: [
        {
          Action: ["states:RedriveExecution"],
          Effect: "Allow",
          Resource: stateMachine.arn.apply((arn) => {
            const stateMachineArnParts = arnParser.parse(arn);
            return arnParser.build({
              ...stateMachineArnParts,
              resource:
                stateMachineArnParts.resource.replace(
                  /stateMachine/,
                  "execution"
                ) + "*",
            });
          }),
        },
      ],
    }),
  });
  const startExecPolicy = new aws.iam.RolePolicy("deployStartExecPolicy", {
    role: deployRole,
    name: "StepFunctionsStartExecutionManagementScopedAccessPolicy",
    policy: pulumi.jsonStringify({
      Version: "2012-10-17",
      Statement: [
        {
          Action: ["states:StartExecution"],
          Effect: "Allow",
          Resource: stateMachine.arn,
        },
        {
          Action: ["states:DescribeExecution", "states:StopExecution"],
          Effect: "Allow",
          Resource: stateMachine.arn.apply((arn) => {
            const stateMachineArnParts = arnParser.parse(arn);
            return arnParser.build({
              ...stateMachineArnParts,
              resource:
                stateMachineArnParts.resource.replace(
                  /stateMachine/,
                  "execution"
                ) + ":*",
            });
          }),
        },
        {
          Effect: "Allow",
          Action: [
            "events:PutTargets",
            "events:PutRule",
            "events:DescribeRule",
          ],
          Resource: [
            // Copy the region and account from the clusterArn
            cluster.arn.apply((clusterArn) => {
              const parts = arnParser.parse(clusterArn);
              return arnParser.build({
                ...parts,
                service: "events",
                resource:
                  "rule/StepFunctionsGetEventsForStepFunctionsExecutionRule",
              });
            }),
          ],
        },
      ],
    }),
  });

  return stateMachine;
}
