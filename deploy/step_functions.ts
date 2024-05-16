import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";
import * as arnParser from "@aws-sdk/util-arn-parser";
import * as time from "@pulumiverse/time";

interface RoleAndPolicies {
  role: aws.iam.Role;
  policies: aws.iam.RolePolicy[];
  policies_settled: pulumi.Resource;
}

export function CreateStateMachineRole(
  namePrefix: string,
  cluster: aws.ecs.Cluster,
  deployApp: aws.ecs.TaskDefinition,
  succeedRun: aws.ecs.TaskDefinition,
  failRun: aws.ecs.TaskDefinition
): RoleAndPolicies {
  const smRole = new aws.iam.Role("stateMachineRole", {
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
  const ecsTaskPolicy = new aws.iam.RolePolicy(
    "stateMachineEcsTaskPolicy",
    {
      role: smRole,
      name: "EcsTaskManagementScopedAccessPolicy",
      policy: pulumi.jsonStringify({
        Version: "2012-10-17",
        Statement: [
          {
            Action: ["ecs:RunTask", "ecs:StopTask", "ecs:DescribeTasks"],
            Effect: "Allow",
            Resource: [
              ...new Set([deployApp.arn, succeedRun.arn, failRun.arn]),
            ],
          },
          {
            Action: ["iam:PassRole"],
            Effect: "Allow",
            Resource: pulumi
              .all([
                deployApp.taskRoleArn,
                succeedRun.taskRoleArn,
                failRun.taskRoleArn,
                deployApp.executionRoleArn,
                succeedRun.executionRoleArn,
                failRun.executionRoleArn,
              ])
              .apply((arns) => [...new Set(arns)]),
          },
          {
            Action: [
              "events:PutTargets",
              "events:PutRule",
              "events:DescribeRule",
            ],
            Effect: "Allow",
            Resource:
              // Copy the region and account from the clusterArn
              cluster.arn.apply((clusterArn) => {
                const parts = arnParser.parse(clusterArn);
                return [
                  arnParser.build({
                    ...parts,
                    service: "events",
                    resource: "rule/StepFunctionsGetEventsForECSTaskRule",
                  }),
                  arnParser.build({
                    ...parts,
                    service: "events",
                    resource:
                      "rule/StepFunctionsGetEventsForStepFunctionsExecutionRule",
                  }),
                ];
              }),
          },
        ],
      }),
    },
    { parent: smRole }
  );
  const xrayPolicy = new aws.iam.RolePolicy(
    "stateMachineXRayPolicy",
    {
      role: smRole,
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
    },
    { parent: smRole }
  );

  // Policies in AWS are eventually consistent, so we need to wait for them to settle before using them
  // See https://github.com/hashicorp/terraform-provider-aws/issues/14008
  // The referenced fix is in v2.69.0 of the provider, but Pulumi uses v1.60.1 (as of this writing)
  const waitForPolicy = new time.Sleep(
    "waitForPolicy",
    { createDuration: "1m" },
    { dependsOn: [ecsTaskPolicy, xrayPolicy] }
  );

  return {
    role: smRole,
    policies: [ecsTaskPolicy, xrayPolicy],
    policies_settled: waitForPolicy,
  };
}

export function CreateDeploymentStateMachine(
  roleAndPolicies: RoleAndPolicies,
  cluster: aws.ecs.Cluster,
  deployApp: aws.ecs.TaskDefinition,
  succeedRun: aws.ecs.TaskDefinition,
  failRun: aws.ecs.TaskDefinition,
  subnets: aws.ec2.Subnet[],
  securityGroups: aws.ec2.SecurityGroup[]
): aws.sfn.StateMachine {
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
        End: true,
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
              Next: "End Run",
            },
            "End Run": {
              Type: "Suceed",
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
        End: true,
      },
    },
    Comment: "Deploys a set of apps (including common)",
  });

  const stateMachine = new aws.sfn.StateMachine(
    "deployment",
    {
      namePrefix: "stacksnap-deployer",
      definition,
      roleArn: roleAndPolicies.role.arn,
    },
    {
      dependsOn: [
        ...roleAndPolicies.policies,
        roleAndPolicies.policies_settled,
      ],
    }
  );

  const redrivePolicy = new aws.iam.RolePolicy(
    "deployRedrivePolicy",
    {
      role: roleAndPolicies.role,
      name: "RedriveDeployPolicy",
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
    },
    { parent: roleAndPolicies.role }
  );
  const startExecPolicy = new aws.iam.RolePolicy(
    "deployStartExecPolicy",
    {
      role: roleAndPolicies.role,
      name: "DeployExecutionPolicy",
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
        ],
      }),
    },
    { parent: roleAndPolicies.role }
  );

  return stateMachine;
}

export function CreateDestroyStateMachine(
  roleAndPolicies: RoleAndPolicies,
  cluster: aws.ecs.Cluster,
  deployApp: aws.ecs.TaskDefinition,
  succeedRun: aws.ecs.TaskDefinition,
  failRun: aws.ecs.TaskDefinition,
  subnets: aws.ec2.Subnet[],
  securityGroups: aws.ec2.SecurityGroup[]
): aws.sfn.StateMachine {
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
    StartAt: "Run all Apps",
    States: {
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
                        "States.Array('destroy', '--job-id', $.input.jobId, '--job-number', $.jobId)",
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
              Next: "End Run",
            },
            "End Run": {
              Type: "Suceed",
            },
          },
        },
        Next: "Run Common",
        Label: "RunallApps",
        MaxConcurrency: 40,
        ItemSelector: {
          "input.$": "$.input",
          "jobId.$": "$$.Map.Item.Value",
        },
        ItemsPath: "$.input.jobNumbers.apps",
        ResultPath: "$.result",
      },
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
                  "States.Array('destroy', '--job-id', $.input.jobId, '--job-number', $.input.jobNumbers.common)",
              },
            ],
          },
        },
        Next: "Succeed Run",
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
        End: true,
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
        End: true,
      },
    },
    Comment: "Destroys a set of apps (including common)",
  });

  const stateMachine = new aws.sfn.StateMachine(
    "destroy",
    {
      namePrefix: "stacksnap-destroyer",
      definition,
      roleArn: roleAndPolicies.role.arn,
    },
    {
      dependsOn: [
        ...roleAndPolicies.policies,
        roleAndPolicies.policies_settled,
      ],
    }
  );

  const redrivePolicy = new aws.iam.RolePolicy(
    "destroyRedrivePolicy",
    {
      role: roleAndPolicies.role,
      name: "RedriveDestroyPolicy",
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
    },
    { parent: roleAndPolicies.role }
  );
  const startExecPolicy = new aws.iam.RolePolicy(
    "destroyStartExecPolicy",
    {
      role: roleAndPolicies.role,
      name: "DestroyExecutionPolicy",
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
        ],
      }),
    },
    { parent: roleAndPolicies.role }
  );

  return stateMachine;
}
