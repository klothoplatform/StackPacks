# StackPacks

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
