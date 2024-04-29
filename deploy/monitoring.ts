import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";


export function createCustomAlarms(logGroup: aws.cloudwatch.LogGroup, snsTopic: aws.sns.Topic): aws.cloudwatch.MetricAlarm[] {
    const alarmNames = [
        "EngineFailure", 
        "IacGenerationFailure", 
        "ReadLiveStateFailure", 
        "PreDeployActionsFailure",
        "DeploymentFailure", 
        "TeardownFailure", 
        "DestroyWorkflowFailure",
        "DeploymentWorkflowFailure"
    ]
    const nonNotificationAlarmNames = [
        "DeploymentFailure", 
        "TeardownFailure", 
    ]
    const namespace = "Stacksnap"

    const alarms: aws.cloudwatch.MetricAlarm[] = [];
    for (const alarmName of alarmNames) {
        createMetricFilter(logGroup.name, alarmName, namespace);
        alarms.push(
            createMetricAlarm({
                alarmName: alarmName,
                metricName: alarmName,
                namespace: namespace,
                threshold: 1,
                triggerActions: nonNotificationAlarmNames.includes(alarmName) ? [] : [snsTopic.arn],
                treatMissingData: "ignore",
            })
        );
    }
    return alarms;
}

export function createALBAlarms(alb: aws.lb.LoadBalancer, snsTopic: aws.sns.Topic): aws.cloudwatch.MetricAlarm[] {
    const alarms: aws.cloudwatch.MetricAlarm[] = [];
    alarms.push(
        createMetricAlarm({
            alarmName: "ALB-5XX-Errors",
            metricName: "HTTPCode_Target_5XX_Count",
            namespace: "AWS/ApplicationELB",
            dimensions: {
                LoadBalancer: alb.name,
            },
            threshold: 1,
            triggerActions: [snsTopic.arn],
        })
    );
    return alarms;
}

interface MetricAlarmArgs {
    metricName: string;
    alarmName: string;
    namespace: string;
    dimensions?: { [key: string]: pulumi.Input<string> };
    threshold: number;
    treatMissingData?: string;
    triggerActions?: pulumi.Input<string>[];
    tags?: { [key: string]: string };
}

// Function to create a metric filter
function createMetricFilter(logGroupName: pulumi.Output<string>, metricName: string, namespace: string) {
    const dimensionKeys = ["ProjectId", "AppId"]; // Keys to extract dimensions from log event
    // Add dimensions from log event
    const dimensions = {};
    for (const key of dimensionKeys) {
        dimensions[key] =`$.${key}`
    }
    const filterPattern = `{$.metric = "${metricName}"}`;

    return new aws.cloudwatch.LogMetricFilter(metricName, {
        logGroupName: logGroupName,
        pattern: filterPattern,
        metricTransformation: {
            name: metricName,
            namespace: namespace,
            value: "$.value",
            unit: "Count",
            dimensions: dimensions
        },
    });
}

// Function to create an alarm for a metric
function createMetricAlarm(args: MetricAlarmArgs): aws.cloudwatch.MetricAlarm {
    return new aws.cloudwatch.MetricAlarm(args.alarmName, {
        comparisonOperator: "GreaterThanOrEqualToThreshold",
        evaluationPeriods: 1,
        actionsEnabled: true,
        alarmActions: args.triggerActions,
        dimensions: args.dimensions,
        insufficientDataActions: args.triggerActions,
        metricName: args.metricName,
        namespace: args.namespace,
        okActions: args.triggerActions,
        period: 60,
        statistic: "Sum",
        threshold: args.threshold,
        tags: args.tags ?? {
            RESOURCE_NAME: args.alarmName,
            GLOBAL_KLOTHO_TAG: "stacksnap-dev",
        },
        treatMissingData: args.treatMissingData ?? "missing",
    });
}