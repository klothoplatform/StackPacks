from typing import List, Optional

from pydantic import BaseModel, Field

from src.project import get_stack_packs
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project


class CostElement(BaseModel):
    app_id: Optional[str] = Field(default=None)
    resource: Optional[str] = Field(default=None)
    category: str
    monthly_cost: float


async def calculate_costs(
    project: Project,
    operation: str,
    request_app_ids: List[str],
):
    match operation:
        case "install":
            app_ids = request_app_ids
        case "uninstall":
            app_ids = [a for a in project.apps if a not in request_app_ids]
        case _:
            raise ValueError(f"Invalid operation: {operation}")

    app_ids = [a for a in app_ids if a != Project.COMMON_APP_NAME]

    sps = get_stack_packs()

    costs: List[CostElement] = []
    for app_id in app_ids:
        app = AppDeployment.get(
            project.id,
            AppDeployment.compose_range_key(
                app_id=app_id, version=project.apps[app_id]
            ),
        )
        if app_id in sps:
            spec = sps[app_id]
        elif app_id == Project.COMMON_APP_NAME:
            spec = CommonStack(
                stack_packs=[sps[a] for a in app_ids if a in sps],
                features=project.features,
            )
        else:
            raise ValueError(f"Unknown app_id: {app_id}")

        constraints = spec.to_constraints(app.get_configurations())
        costs.extend(await calculate_costs_single(app_id, constraints))

    return costs


async def calculate_costs_single(app_id: str, constraints: List[dict]):
    """Calculate the costs from a snapshot of the cost estimates
    https://calculator.aws/#/estimate?id=be13a20b606e11a56f03984428088586bba8ab01
    """
    costs: List[CostElement] = []
    for constraint in constraints:
        # only calculate costs for added resources - edges & configuration don't currently have costs
        if not (
            constraint["operator"] in ["must_exist", "add"]
            and constraint["scope"] == "application"
        ):
            continue

        res_type = constraint["node"].split(":")[1]

        match res_type:
            case "subnet":
                is_public = bool(
                    [
                        c
                        for c in constraints
                        if c["scope"] == "resource"
                        and c.get("property", None) == "Type"
                        and c.get("value", None) == "public"
                        and c["target"] == constraint["node"]
                    ]
                )
                if is_public:
                    # cost for the nat_gateway, but since it's not explicitly added
                    # and we don't want to run the engine, use this as a proxy
                    # since the engine creates 1 nat_gateway per public subnet
                    costs.append(
                        CostElement(
                            app_id=app_id,
                            category="network",
                            monthly_cost=33.08,
                            resource="aws:nat_gateway",
                        )
                    )

            case "rds_instance":
                costs.append(
                    CostElement(
                        app_id=app_id,
                        category="storage",
                        resource=constraint["node"],
                        monthly_cost=49.28,
                    )
                )

            case "memorydb_cluster":
                costs.append(
                    CostElement(
                        app_id=app_id,
                        category="storage",
                        resource=constraint["node"],
                        monthly_cost=36.04,
                    )
                )

            case "efs_file_system":
                costs.append(
                    CostElement(
                        app_id=app_id,
                        category="storage",
                        resource=constraint["node"],
                        monthly_cost=12.5,
                    )
                )

            case "load_balancer":
                costs.append(
                    CostElement(
                        app_id=app_id,
                        category="network",
                        resource=constraint["node"],
                        monthly_cost=16.66,
                    )
                )

            case "cloudfront_distribution":
                costs.append(
                    CostElement(
                        app_id=app_id,
                        category="network",
                        resource=constraint["node"],
                        monthly_cost=0.32,
                    )
                )

            case "ecr_image":
                costs.append(
                    CostElement(
                        app_id=app_id,
                        category="compute",
                        resource=constraint["node"],
                        monthly_cost=0.6,
                    )
                )
            case "ecs_service":
                # We set some defaults so that we dont fail on cost calculation
                cpu = 0.512
                memory = 2.048
                count = 1
                tasks = {}
                task_def = None
                for c in constraints:
                    if c["scope"] == "resource" and c["target"].startswith(
                        "aws:ecs_task_definition"
                    ):
                        tasks[c["target"]] = {}
                        if c["property"] == "Cpu":
                            tasks[c["target"]]["Cpu"] = c["value"]
                        if c["property"] == "Memory":
                            tasks[c["target"]]["Memory"] = c["value"]
                    if c["scope"] == "resource" and c["target"] == constraint["node"]:
                        if c["property"] == "TaskDefinition":
                            task_def = c["value"]
                        if c["property"] == "DesiredCount":
                            count = c["value"]

                task_definition = tasks.get(task_def)
                if task_definition:
                    cpu = task_definition.get("Cpu", cpu)
                    memory = task_definition.get("Memory", memory)

                costs.append(
                    CostElement(
                        app_id=app_id,
                        category="compute",
                        resource=constraint["node"],
                        # the below costs are per hour so average for a month
                        monthly_cost=count * 730 * (cpu * 0.04048 + memory * 0.004445),
                    )
                )

    return costs
