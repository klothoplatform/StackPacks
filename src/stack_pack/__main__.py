import argparse
import yaml
from pydantic_yaml import parse_yaml_file_as

from . import StackPack, ConfigValues, get_stack_packs

parser = argparse.ArgumentParser()
parser.add_argument("template", type=str, help="Path to the stack pack template")
parser.add_argument(
    "--config", "-c", type=str, action="append", help="Configuration values"
)
parser.add_argument(
    "--config-file", "-f", type=str, help="Path to the configuration file"
)

args = parser.parse_args()

sps = get_stack_packs()
print(f"Stack Packs: {sps.keys()}")

sp = parse_yaml_file_as(StackPack, args.template)

values = ConfigValues()
if args.config:
    for c in args.config:
        k, v = c.split("=")
        if v.lower() in ["true", "false"]:
            v = v.lower() == "true"
        elif v.isdigit():
            v = int(v)
        elif v.isnumeric():
            v = float(v)
        values[k] = v

print(f"User config: {values}")

c = sp.to_constraints(values)
print(yaml.dump(c))

pulumi = sp.get_pulumi_configs(values)
print("Pulumi Configs:")
print(yaml.dump(pulumi))
