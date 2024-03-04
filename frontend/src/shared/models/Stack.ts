/*
 * stackPacks: {name -> user_confg_map} dict[str <name of stack pack>, dict[str <config keys from the stackpack.configuration>, Any]]
 * eg: {"mattermost": {"Cpu": 1024, "DBPassword": "hunter2"}}
 * note: versioning TBD, solve later [maybe {"mattermost": {"__version": 2}} ?]
 * region
 * aws iam role
 * arn
 * external id
 * deploymentStatus
 * deploymentStatusReason
 * owner
 * creationTime
 */

export interface Stack {
  assumedRoleArn: string;
  assumedRoleExternalId: string;
  createdAt: number;
  createdBy: string;
  status: "not-started" | "running" | "succeeded" | "failed";
  statusReason: string;
  id: string;
  name: string;
  owner: string;
  configuration: Configuration;
  region: string;
}

export interface Configuration {
  //stack pack name
  [key: string]: {
    // config key (e.g. CPU)
    [key: string]: any;
  };
}
