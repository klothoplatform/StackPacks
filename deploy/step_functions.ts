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
    awsvpcConfiguration: {
      subnets: subnets.map((subnet) => subnet.id),
      securityGroups: securityGroups.map((sg) => sg.id),
    },
  };

  // input:
  // {
  //   "projectId": "123",
  //   "runId": "123",
  //   "jobIds": {
  //     "common": "1",
  //     "apps": ["2", "3"]
  //    },
  // }
  const definition = pulumi
    .all([cluster.arn, deployApp.arn, succeedRun.arn, failRun.arn])
    .apply(([clusterArn, deployAppArn, succeedRunArn, failRunArn]) => {
      return JSON.stringify({
        StartAt: "Run Common",
        States: {
          "Run Common": {
            Type: "Task",
            Resource: "arn:aws:states:::ecs:runTask.sync",
            Parameters: {
              LaunchType: "FARGATE",
              Cluster: clusterArn,
              TaskDefinition: deployAppArn,
              NetworkConfiguration: networkConfig,
              Overrides: {
                ContainerOverrides: [
                  {
                    Name: "stacksnap-cli",
                    "Command.$":
                      "States.Array('deploy', '--run-id', $.input.runId, '--job-number', $.input.jobIds.common)",
                    // [
                    //   "deploy",
                    //   "--run-id",
                    //   "$.input.runId",
                    //   "--job-number",
                    //   "$.input.jobIds.common",
                    // ],
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
                ResultPath: "$.input",
              },
            ],
            ResultPath: "$.input",
          },
          "Fail Run (common)": {
            Type: "Task",
            Resource: "arn:aws:states:::ecs:runTask.sync",
            Parameters: {
              LaunchType: "FARGATE",
              Cluster: clusterArn,
              TaskDefinition: failRunArn,
              NetworkConfiguration: networkConfig,
              Overrides: {
                ContainerOverrides: [
                  {
                    Name: "stacksnap-cli",
                    "Command.$":
                      "States.Array('complete-workflow', '--project-id', $.input.projectId, '--run-id', $.input.runId)",
                    // [
                    //   "complete-workflow",
                    //   "--project-id",
                    //   "$.input.projectId",
                    //   "--run-id",
                    //   "$.input.runId",
                    // ],
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
                Mode: "DISTRIBUTED",
                ExecutionType: "STANDARD",
              },
              StartAt: "Run App",
              States: {
                "Run App": {
                  Type: "Task",
                  Resource: "arn:aws:states:::ecs:runTask.sync",
                  Parameters: {
                    LaunchType: "FARGATE",
                    Cluster: clusterArn,
                    TaskDefinition: deployAppArn,
                    NetworkConfiguration: networkConfig,
                    Overrides: {
                      ContainerOverrides: [
                        {
                          Name: "stacksnap-cli",
                          "Command.$":
                            "States.Array('deploy', '--run-id', $.input.runId, '--job-number', $$.Map.Item)",
                          // [
                          //   "deploy",
                          //   "--run-id",
                          //   "$.input.runId",
                          //   "--job-number",
                          //   "$$.Map.Item",
                          // ],
                        },
                      ],
                    },
                  },
                  Catch: [
                    {
                      ErrorEquals: ["States.ALL"],
                      Next: "Fail Run (app)",
                      ResultPath: "$.input",
                    },
                  ],
                  End: true,
                  ResultPath: "$.input",
                },
                "Fail Run (app)": {
                  Type: "Task",
                  Resource: "arn:aws:states:::ecs:runTask.sync",
                  Parameters: {
                    LaunchType: "FARGATE",
                    Cluster: clusterArn,
                    TaskDefinition: failRunArn,
                    NetworkConfiguration: networkConfig,
                    Overrides: {
                      ContainerOverrides: [
                        {
                          Name: "stacksnap-cli",
                          "Command.$":
                            "States.Array('complete-workflow', '--project-id', $.input.projectId, '--run-id', $.input.runId)",
                          // [
                          //   "complete-workflow",
                          //   "--project-id",
                          //   "$.input.projectId",
                          //   "--run-id",
                          //   "$.input.runId",
                          // ],
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
            MaxConcurrency: 100,
            ItemsPath: "$.input.jobIds.apps",
            ResultPath: "$.input",
          },
          "Succeed Run": {
            Type: "Task",
            Resource: "arn:aws:states:::ecs:runTask.sync",
            Parameters: {
              LaunchType: "FARGATE",
              Cluster: clusterArn,
              TaskDefinition: succeedRunArn,
              NetworkConfiguration: networkConfig,
              Overrides: {
                ContainerOverrides: [
                  {
                    Name: "stacksnap-cli",
                    "Command.$":
                      "States.Array('complete-workflow', '--project-id', $.input.projectId, '--run-id', $.input.runId)",
                    // [
                    //   "complete-workflow",
                    //   "--project-id",
                    //   "$.input.projectId",
                    //   "--run-id",
                    //   "$.input.runId",
                    // ],
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
                ) + "/*",
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
          // TODO can this be restricted to the state machine? The generated one does this '*', so maybe not a concern
          Resource: `*`,
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
