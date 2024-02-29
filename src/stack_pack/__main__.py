import argparse
import yaml
from pydantic_yaml import parse_yaml_file_as

from . import StackPack, ConfigValues

parser = argparse.ArgumentParser()
parser.add_argument("template", type=str, help="Path to the stack pack template")
parser.add_argument("--config", "-c", type=str, nargs="*", help="Configuration values")
parser.add_argument(
    "--config-file", "-f", type=str, help="Path to the configuration file"
)

args = parser.parse_args()

sp = parse_yaml_file_as(StackPack, args.template)

values = ConfigValues()
if args.config:
    for c in args.config:
        k, v = c.split("=")
        values[k] = v

print(f"User config: {values}")

c = sp.to_constraints(values)
print(yaml.dump(c))
