import * as aws from '@pulumi/aws'
import * as awsInputs from '@pulumi/aws/types/input'
import * as command from '@pulumi/command'
import * as docker from '@pulumi/docker'
import * as inputs from '@pulumi/aws/types/input'
import * as pulumi from '@pulumi/pulumi'
import { OutputInstance } from '@pulumi/pulumi'


const kloConfig = new pulumi.Config('klo')
const protect = kloConfig.getBoolean('protect') ?? false
const awsConfig = new pulumi.Config('aws')
const awsProfile = awsConfig.get('profile')
const accountId = pulumi.output(aws.getCallerIdentity({}))
const region = pulumi.output(aws.getRegion({}))

const cloudfront_origin_access_identity_0 = new aws.cloudfront.OriginAccessIdentity("cloudfront_origin_access_identity-0", {
        comment: "this is needed to set up S3 polices so that the S3 bucket is not public",
    })
const deployments = new aws.dynamodb.Table(
        "deployments",
        {
            attributes: [
    {
        name: "id",
        type: "S"
    },
    {
        name: "iac_stack_composite_key",
        type: "S"
    },
]

,
            hashKey: "id",
            rangeKey: "iac_stack_composite_key",
            billingMode: "PAY_PER_REQUEST",
            tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "dynamodb_table_7"},
        },
        { protect: protect }
    )
const pulumistacks = new aws.dynamodb.Table(
        "pulumistacks",
        {
            attributes: [
    {
        name: "id",
        type: "S"
    },
    {
        name: "name",
        type: "S"
    },
]

,
            hashKey: "project_name",
            rangeKey: "name",
            billingMode: "PAY_PER_REQUEST",
            tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "dynamodb_table_8"},
        },
        { protect: protect }
    )
const userapps = new aws.dynamodb.Table(
        "userapps",
        {
            attributes: [
    {
        name: "id",
        type: "S"
    },
    {
        name: "version",
        type: "N"
    },
]

,
            hashKey: "app_id",
            rangeKey: "version",
            billingMode: "PAY_PER_REQUEST",
            tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "dynamodb_table_9"},
        },
        { protect: protect }
    )
const userpacks = new aws.dynamodb.Table(
        "userpacks",
        {
            attributes: [
    {
        name: "id",
        type: "S"
    },
]

,
            hashKey: "id",
            billingMode: "PAY_PER_REQUEST",
            tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "dynamodb_table_10"},
        },
        { protect: protect }
    )
const ecs_service_0_ecs_service_0_ecr_repo = new aws.ecr.Repository("ecs_service_0-ecs_service_0-ecr_repo", {
        imageScanningConfiguration: {
            scanOnPush: true,
        },
        imageTagMutability: 'MUTABLE',
        forceDelete: true,
        encryptionConfigurations: [{ encryptionType: 'KMS' }],
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "ecs_service_0-ecs_service_0-ecr_repo"},
    })
const ecs_cluster_0 = new aws.ecs.Cluster("ecs_cluster-0", {
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "ecs_cluster-0"},
    })
const subnet_0_route_table_nat_gateway_elastic_ip = new aws.ec2.Eip("subnet-0-route_table-nat_gateway-elastic_ip", {
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-0-route_table-nat_gateway-elastic_ip"},
    })
const subnet_1_route_table_nat_gateway_elastic_ip = new aws.ec2.Eip("subnet-1-route_table-nat_gateway-elastic_ip", {
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-1-route_table-nat_gateway-elastic_ip"},
    })
const ecs_service_0_log_group = new aws.cloudwatch.LogGroup("ecs_service_0-log-group", {
        name: "/aws/ecs/ecs_service_0",
        retentionInDays: 5,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "ecs_service_0-log-group"},
    })
const region_0 = pulumi.output(aws.getRegion({}))
const iac_store = new aws.s3.Bucket(
        "iac-store",
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
            tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "s3-bucket-15"},
        },
        { protect: protect }
    )
export const iac_store_BucketName = iac_store.bucket
const stack_snap_binaries = new aws.s3.Bucket(
        "stack-snap-binaries",
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
            tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "s3-bucket-21"},
        },
        { protect: protect }
    )
export const stack_snap_binaries_BucketName = stack_snap_binaries.bucket
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
            tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "s3-bucket-18"},
        },
        { protect: protect }
    )
export const stacksnap_ui_BucketName = stacksnap_ui.bucket
const vpc_0 = new aws.ec2.Vpc("vpc-0", {
        cidrBlock: "10.0.0.0/16",
        enableDnsHostnames: true,
        enableDnsSupport: true,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "vpc-0"},
    })
const ecs_service_0_ecs_service_0 = (() => {
        const pullBaseImage = new command.local.Command(
            `${"ecs_service_0-ecs_service_0"}-pull-base-image-${Date.now()}`,
            {
                create: pulumi.interpolate`docker pull ${"python:3.11-slim-bookworm"} --platform ${"linux/amd64"}`,
            }
        )
        const base = new docker.Image(
            `${"ecs_service_0-ecs_service_0"}-base`,
            {
                build: {
                    context: ".",
                    dockerfile: "Dockerfile",
                    platform: "linux/amd64",
                },
                skipPush: true,
                imageName: pulumi.interpolate`${ecs_service_0_ecs_service_0_ecr_repo.repositoryUrl}:base`,
            },
            {
                dependsOn: pullBaseImage,
            }
        )

        const sha256 = new command.local.Command(
            `${"ecs_service_0-ecs_service_0"}-base-get-sha256-${Date.now()}`,
            { create: pulumi.interpolate`docker image inspect -f {{.ID}} ${base.imageName}` },
            { parent: base }
        ).stdout.apply((id) => id.substring(7))

        return new docker.Image(
            "ecs_service_0-ecs_service_0",
            {
                build: {
                    context: ".",
                    dockerfile: "Dockerfile",
                    platform: "linux/amd64",
                },
                registry: aws.ecr
                    .getAuthorizationTokenOutput(
                        { registryId: ecs_service_0_ecs_service_0_ecr_repo.registryId },
                        { async: true }
                    )
                    .apply((registryToken) => {
                        return {
                            server: ecs_service_0_ecs_service_0_ecr_repo.repositoryUrl,
                            username: registryToken.userName,
                            password: registryToken.password,
                        }
                    }),
                imageName: pulumi.interpolate`${ecs_service_0_ecs_service_0_ecr_repo.repositoryUrl}:${sha256}`,
            },
            { parent: base }
        )
    })()
const availability_zone_0 = pulumi.output(
        aws.getAvailabilityZones({
            state: 'available',
        })
    ).names[0]
const availability_zone_1 = pulumi.output(
        aws.getAvailabilityZones({
            state: 'available',
        })
    ).names[1]
const s3_bucket_policy_0 = new aws.s3.BucketPolicy("s3_bucket_policy-0", {
        bucket: stacksnap_ui.id,
        policy: {Statement: [{Action: ["s3:GetObject"], Effect: "Allow", Principal: {AWS: [cloudfront_origin_access_identity_0.iamArn]}, Resource: [pulumi.interpolate`${stacksnap_ui.arn}/*`]}], Version: "2012-10-17"},
    })
const internet_gateway_0 = new aws.ec2.InternetGateway("internet_gateway-0", {
        vpcId: vpc_0.id,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "internet_gateway-0"},
    })
const ecs_service_0_security_group = new aws.ec2.SecurityGroup("ecs_service_0-security_group", {
        name: "ecs_service_0-security_group",
        vpcId: vpc_0.id,
        egress: [{cidrBlocks: ["0.0.0.0/0"], description: "Allows all outbound IPv4 traffic", fromPort: 0, protocol: "-1", toPort: 0}],
        ingress: [{cidrBlocks: ["10.0.0.0/18"], description: "Allow ingress traffic from ip addresses within the subnet subnet-2", fromPort: 0, protocol: "-1", toPort: 0}, {cidrBlocks: ["10.0.64.0/18"], description: "Allow ingress traffic from ip addresses within the subnet subnet-3", fromPort: 0, protocol: "-1", toPort: 0}, {description: "Allow ingress traffic from within the same security group", fromPort: 0, protocol: "-1", self: true, toPort: 0}],
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "ecs_service_0-security_group"},
    })
const load_balancer_2_security_group = new aws.ec2.SecurityGroup("load-balancer-2-security_group", {
        name: "load-balancer-2-security_group",
        vpcId: vpc_0.id,
        egress: [{cidrBlocks: ["0.0.0.0/0"], description: "Allows all outbound IPv4 traffic", fromPort: 0, protocol: "-1", toPort: 0}],
        ingress: [{cidrBlocks: ["0.0.0.0/0"], description: "Allow ingress traffic from within the same security group", fromPort: 0, protocol: "-1", toPort: 0}, {description: "Allow ingress traffic from within the same security group", fromPort: 0, protocol: "-1", self: true, toPort: 0}],
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "load-balancer-2-security_group"},
    })
const security_group_subnet_0_deploy_logs = new aws.ec2.SecurityGroup("subnet-0-deploy-logs", {
        name: "subnet-0-deploy-logs",
        vpcId: vpc_0.id,
        egress: [{cidrBlocks: ["0.0.0.0/0"], description: "Allows all outbound IPv4 traffic", fromPort: 0, protocol: "-1", toPort: 0}],
        ingress: [{cidrBlocks: ["10.0.128.0/18"], description: "Allow ingress traffic from ip addresses within the subnet subnet-0", fromPort: 0, protocol: "-1", toPort: 0}, {description: "Allow ingress traffic from within the same security group", fromPort: 0, protocol: "-1", self: true, toPort: 0}],
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-0-deploy-logs"},
    })
const security_group_subnet_1_deploy_logs = new aws.ec2.SecurityGroup("subnet-1-deploy-logs", {
        name: "subnet-1-deploy-logs",
        vpcId: vpc_0.id,
        egress: [{cidrBlocks: ["0.0.0.0/0"], description: "Allows all outbound IPv4 traffic", fromPort: 0, protocol: "-1", toPort: 0}],
        ingress: [{cidrBlocks: ["10.0.192.0/18"], description: "Allow ingress traffic from ip addresses within the subnet subnet-1", fromPort: 0, protocol: "-1", toPort: 0}, {description: "Allow ingress traffic from within the same security group", fromPort: 0, protocol: "-1", self: true, toPort: 0}],
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-1-deploy-logs"},
    })
const default_rule_stack_snap = (() => {
        const tg = new aws.lb.TargetGroup("default-rule-stack-snap", {
            port: 80,
            protocol: "HTTP",
            targetType: "ip",
            vpcId: vpc_0.id,
            healthCheck: {
    enabled: true,
    healthyThreshold: 5,
    interval: 30,
    protocol: "HTTP",
    timeout: 5,
    unhealthyThreshold: 2
},
            tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "default-rule-stack-snap"},
        })
        return tg
    })()
const deploy_logs = new aws.efs.FileSystem(
        "deploy-logs",
        {
            encrypted: true,
            performanceMode: "generalPurpose",
            throughputMode: "bursting",
            tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "efs_file_system_5"},
        },
        {
            dependsOn: [],
        }
    )
const subnet_2_route_table = new aws.ec2.RouteTable("subnet-2-route_table", {
        vpcId: vpc_0.id,
        routes: [
    {
        cidrBlock: "0.0.0.0/0",
        gatewayId: internet_gateway_0.id
    },
]

,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-2-route_table"},
    })
const subnet_3_route_table = new aws.ec2.RouteTable("subnet-3-route_table", {
        vpcId: vpc_0.id,
        routes: [
    {
        cidrBlock: "0.0.0.0/0",
        gatewayId: internet_gateway_0.id
    },
]

,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-3-route_table"},
    })
const stack_snap_deploy_logs = new aws.efs.AccessPoint("stack-snap-deploy-logs", {
        fileSystemId: deploy_logs.id,
        posixUser: {gid: 1000, uid: 1000},
        rootDirectory: {creationInfo: {ownerGid: 1000, ownerUid: 1000, permissions: "777"}, path: "/mnt/logs"},
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "stack-snap-deploy-logs"},
    })
const ecs_service_0_execution_role = new aws.iam.Role("ecs_service_0-execution-role", {
        assumeRolePolicy: pulumi.jsonStringify({Statement: [{Action: ["sts:AssumeRole"], Effect: "Allow", Principal: {Service: ["ecs-tasks.amazonaws.com"]}}], Version: "2012-10-17"}),
        inlinePolicies: [
    {
        name: "deploy-logs-policy",
        policy: pulumi.jsonStringify({Statement: [{Action: ["efs:Client*"], Effect: "Allow", Resource: [deploy_logs.arn]}], Version: "2012-10-17"})
    },
    {
        name: "pulumistacks-policy",
        policy: pulumi.jsonStringify({Statement: [{Action: ["dynamodb:*"], Effect: "Allow", Resource: [pulumistacks.arn, pulumi.interpolate`${pulumistacks.arn}/stream/*`, pulumi.interpolate`${pulumistacks.arn}/backup/*`, pulumi.interpolate`${pulumistacks.arn}/export/*`, pulumi.interpolate`${pulumistacks.arn}/index/*`]}], Version: "2012-10-17"})
    },
    {
        name: "userpacks-policy",
        policy: pulumi.jsonStringify({Statement: [{Action: ["dynamodb:*"], Effect: "Allow", Resource: [userpacks.arn, pulumi.interpolate`${userpacks.arn}/stream/*`, pulumi.interpolate`${userpacks.arn}/backup/*`, pulumi.interpolate`${userpacks.arn}/export/*`, pulumi.interpolate`${userpacks.arn}/index/*`]}], Version: "2012-10-17"})
    },
    {
        name: "userapps-policy",
        policy: pulumi.jsonStringify({Statement: [{Action: ["dynamodb:*"], Effect: "Allow", Resource: [userapps.arn, pulumi.interpolate`${userapps.arn}/stream/*`, pulumi.interpolate`${userapps.arn}/backup/*`, pulumi.interpolate`${userapps.arn}/export/*`, pulumi.interpolate`${userapps.arn}/index/*`]}], Version: "2012-10-17"})
    },
    {
        name: "deployments-policy",
        policy: pulumi.jsonStringify({Statement: [{Action: ["dynamodb:*"], Effect: "Allow", Resource: [deployments.arn, pulumi.interpolate`${deployments.arn}/stream/*`, pulumi.interpolate`${deployments.arn}/backup/*`, pulumi.interpolate`${deployments.arn}/export/*`, pulumi.interpolate`${deployments.arn}/index/*`]}], Version: "2012-10-17"})
    },
    {
        name: "iac-store-policy",
        policy: pulumi.jsonStringify({Statement: [{Action: ["s3:*"], Effect: "Allow", Resource: [iac_store.arn, pulumi.interpolate`${iac_store.arn}/*`]}], Version: "2012-10-17"})
    },
    {
        name: "stack-snap-binaries-policy",
        policy: pulumi.jsonStringify({Statement: [{Action: ["s3:*"], Effect: "Allow", Resource: [stack_snap_binaries.arn, pulumi.interpolate`${stack_snap_binaries.arn}/*`]}], Version: "2012-10-17"})
    },
],
        managedPolicyArns: [
            ...["arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"],
        ],
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "ecs_service_0-execution-role"},
    })
const subnet_2 = new aws.ec2.Subnet("subnet-2", {
        vpcId: vpc_0.id,
        cidrBlock: "10.0.0.0/18",
        availabilityZone: availability_zone_0,
        mapPublicIpOnLaunch: false,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-2"},
    })
const subnet_3 = new aws.ec2.Subnet("subnet-3", {
        vpcId: vpc_0.id,
        cidrBlock: "10.0.64.0/18",
        availabilityZone: availability_zone_1,
        mapPublicIpOnLaunch: false,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-3"},
    })
const ecs_service_0 = new aws.ecs.TaskDefinition("ecs_service_0", {
        family: "ecs_service_0",
        cpu: "256",
        memory: "512",
        networkMode: "awsvpc",
        requiresCompatibilities: ["FARGATE"],
        executionRoleArn: ecs_service_0_execution_role.arn,
        taskRoleArn: ecs_service_0_execution_role.arn,
        volumes: [
    { 
        name: "stack-snap-deploy-logs",
        efsVolumeConfiguration: {
            fileSystemId: deploy_logs.id,
            authorizationConfig: {
                accessPointId: stack_snap_deploy_logs.id,
                iam: "ENABLED",
            },
            transitEncryption: "ENABLED",
        },
    },
],
        containerDefinitions: pulumi.jsonStringify([
    {
        cpu: 256,
        environment: [
            {
                name: "PULUMISTACKS_TABLE_NAME",
                value: pulumistacks.name,
            },
            {
                name: "USERPACKS_TABLE_NAME",
                value: userpacks.name,
            },
            {
                name: "USERAPPS_TABLE_NAME",
                value: userapps.name,
            },
            {
                name: "DEPLOYMENTS_TABLE_NAME",
                value: deployments.name,
            },
            {
                name: "IAC_STORE_BUCKET_NAME",
                value: iac_store.bucket,
            },
            {
                name: "STACK_SNAP_BINARIES_BUCKET_NAME",
                value: stack_snap_binaries.bucket,
            },
        ],
        essential: true,
        image: ecs_service_0_ecs_service_0.imageName,
        logConfiguration: {
            logDriver: "awslogs",
            options: {
                "awslogs-group": "/aws/ecs/ecs_service_0",
                "awslogs-region": region_0.apply((o) => o.name),
                "awslogs-stream-prefix": "ecs_service_0-ecs_service_0",
            },
        },
        memory: 512,
        mountPoints: [
            {
                containerPath: "/app/deployments",
                readOnly: false,
                sourceVolume: "stack-snap-deploy-logs",
            },
        ],
        name: "ecs_service_0",
        portMappings: [
            {
                containerPort: 80,
                hostPort: 80,
                protocol: "TCP",
            },
        ],        
    },
]),
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "ecs_service_0"},
    })
const efs_mount_target_subnet_0_deploy_logs = new aws.efs.MountTarget("subnet-0-deploy-logs", {
        fileSystemId: deploy_logs.id,
        subnetId: subnet_2.id,
        securityGroups: [security_group_subnet_0_deploy_logs]?.map((sg) => sg.id),
    })
const subnet_0_route_table_nat_gateway = new aws.ec2.NatGateway("subnet-0-route_table-nat_gateway", {
        allocationId: subnet_0_route_table_nat_gateway_elastic_ip.id,
        subnetId: subnet_2.id,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-0-route_table-nat_gateway"},
    })
const subnet_2_subnet_2_route_table = new aws.ec2.RouteTableAssociation("subnet-2-subnet-2-route_table", {
        subnetId: subnet_2.id,
        routeTableId: subnet_2_route_table.id,
    })
const efs_mount_target_subnet_1_deploy_logs = new aws.efs.MountTarget("subnet-1-deploy-logs", {
        fileSystemId: deploy_logs.id,
        subnetId: subnet_3.id,
        securityGroups: [security_group_subnet_1_deploy_logs]?.map((sg) => sg.id),
    })
const load_balancer_2 = new aws.lb.LoadBalancer("load-balancer-2", {
        internal: false,
        loadBalancerType: "application",
        subnets: [subnet_2, subnet_3].map((subnet) => subnet.id),
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "load-balancer-2"},
        securityGroups: [load_balancer_2_security_group].map((sg) => sg.id),
    })
export const load_balancer_2_DomainName = load_balancer_2.dnsName
const subnet_1_route_table_nat_gateway = new aws.ec2.NatGateway("subnet-1-route_table-nat_gateway", {
        allocationId: subnet_1_route_table_nat_gateway_elastic_ip.id,
        subnetId: subnet_3.id,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-1-route_table-nat_gateway"},
    })
const subnet_3_subnet_3_route_table = new aws.ec2.RouteTableAssociation("subnet-3-subnet-3-route_table", {
        subnetId: subnet_3.id,
        routeTableId: subnet_3_route_table.id,
    })
const subnet_0_route_table = new aws.ec2.RouteTable("subnet-0-route_table", {
        vpcId: vpc_0.id,
        routes: [
  {
    cidrBlock: "0.0.0.0/0",
    natGatewayId: subnet_0_route_table_nat_gateway.id
  },
]

,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-0-route_table"},
    })
const stacksnap = new aws.cloudfront.Distribution("stacksnap", {
        origins: [{domainName: stacksnap_ui.bucketRegionalDomainName, originId: "stacksnap-ui", s3OriginConfig: {originAccessIdentity: cloudfront_origin_access_identity_0.cloudfrontAccessIdentityPath}}, {customOriginConfig: {httpPort: 80, httpsPort: 443, originProtocolPolicy: "http-only", originSslProtocols: ["TLSv1.2", "TLSv1", "SSLv3", "TLSv1.1"]}, domainName: load_balancer_2.dnsName, originId: "load-balancer-2"}],
        enabled: true,
        viewerCertificate: {cloudfrontDefaultCertificate: true},
        orderedCacheBehaviors: [{allowedMethods: ["GET", "HEAD", "OPTIONS"], cachedMethods: ["GET", "HEAD"], defaultTtl: 0, forwardedValues: {cookies: {forward: "none"}, queryString: true}, maxTtl: 0, minTtl: 0, pathPattern: "/*", smoothStreaming: false, targetOriginId: "load-balancer-2", viewerProtocolPolicy: "redirect-to-https"}],
        defaultCacheBehavior: {allowedMethods: ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"], cachedMethods: ["HEAD", "GET"], defaultTtl: 3600, forwardedValues: {cookies: {forward: "none"}, queryString: true}, maxTtl: 86400, minTtl: 0, targetOriginId: "stacksnap-ui", viewerProtocolPolicy: "allow-all"},
        restrictions: {geoRestriction: {restrictionType: "none"}},
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "cloudfront_distribution_17"},
    })
export const stacksnap_Domain = stacksnap.domainName
const load_balancer_2_listener_0 = new aws.lb.Listener("load_balancer_2-listener-0", {
        loadBalancerArn: load_balancer_2.arn,
        defaultActions: [
    {
        targetGroupArn: default_rule_stack_snap.arn,
        type: "forward",
    },
]

,
        port: 80,
        protocol: "HTTP",
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "load_balancer_2-listener-0"},
    })
const subnet_1_route_table = new aws.ec2.RouteTable("subnet-1-route_table", {
        vpcId: vpc_0.id,
        routes: [
  {
    cidrBlock: "0.0.0.0/0",
    natGatewayId: subnet_1_route_table_nat_gateway.id
  },
]

,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-1-route_table"},
    })
const subnet_0 = new aws.ec2.Subnet("subnet-0", {
        vpcId: vpc_0.id,
        cidrBlock: "10.0.128.0/18",
        availabilityZone: availability_zone_0,
        mapPublicIpOnLaunch: false,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-0"},
    })
const default_rule = new aws.lb.ListenerRule("default-rule", {
        listenerArn: load_balancer_2_listener_0.arn,
        priority: 1,
        conditions: [{pathPattern: {values: ["/*"]}}],
        actions: [
    {
        type: "forward",
        targetGroupArn: default_rule_stack_snap.arn,
    },
]

,
        tags: {Name: "default-rule"},
    })
const subnet_1 = new aws.ec2.Subnet("subnet-1", {
        vpcId: vpc_0.id,
        cidrBlock: "10.0.192.0/18",
        availabilityZone: availability_zone_1,
        mapPublicIpOnLaunch: false,
        tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "subnet-1"},
    })
const subnet_0_subnet_0_route_table = new aws.ec2.RouteTableAssociation("subnet-0-subnet-0-route_table", {
        subnetId: subnet_0.id,
        routeTableId: subnet_0_route_table.id,
    })
const stack_snap = new aws.ecs.Service(
        "stack-snap",
        {
            launchType: "FARGATE",
            cluster: ecs_cluster_0.arn,
            desiredCount: 1,
            forceNewDeployment: true,
            loadBalancers: [
    {
        containerPort: 80,
        targetGroupArn: default_rule_stack_snap.arn,
        containerName: "ecs_service_0",
    },
]

,
            networkConfiguration: {
                subnets: [subnet_0, subnet_1].map((sn) => sn.id),
                securityGroups: [ecs_service_0_security_group].map((sg) => sg.id),
            },
            taskDefinition: ecs_service_0.arn,
            waitForSteadyState: true,
            tags: {GLOBAL_KLOTHO_TAG: "", RESOURCE_NAME: "ecs_service_0"},
        },
        { dependsOn: [default_rule_stack_snap, ecs_cluster_0, ecs_service_0, ecs_service_0_security_group, subnet_0, subnet_1] }
    )
const subnet_1_subnet_1_route_table = new aws.ec2.RouteTableAssociation("subnet-1-subnet-1-route_table", {
        subnetId: subnet_1.id,
        routeTableId: subnet_1_route_table.id,
    })
