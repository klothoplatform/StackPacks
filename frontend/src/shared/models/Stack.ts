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
  id: string;
  configurationErrors: ConfigurationError[];
  createdBy: string;
  awsConfig: {
    iamRoleArn: string;
    externalId: string;
    iamPolicy: string;
  };
  deploymentStatus: "not-started" | "running" | "succeeded" | "failed";
  deploymentStatusReason: string;
  name: string;
  owner: string;
  stackPacks: Configuration;
  region: string;
}

export interface Configuration {
  //stack pack name
  [key: string]: {
    // config key (e.g. CPU)
    [key: string]: any;
  };
}

export interface ConfigurationError {
  property: string;
  value?: any;
  error: {
    chain: string[];
  };
  errorCode: string;
  validationError: string;
}
