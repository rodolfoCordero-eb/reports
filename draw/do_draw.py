import os
from .draw_strategy import DrawStrategy
class do_strategy(DrawStrategy):
    def draw(self, elements, path, region):
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, f"{region}.dot")

        lines = [
            f'digraph "{region}" {{',
            '  rankdir=LR;',
            '  node [shape=box, style=filled, fillcolor=lightgrey];',
        ]

        vpc_name = "VPC"
        if elements.get("vpcs"):
            vpc = elements["vpcs"][0]
            vpc_name = next((tag["Value"] for tag in vpc.get("Tags", []) if tag["Key"] == "Name"), vpc["VpcId"])

        lines.append(f'  subgraph cluster_vpc {{')
        lines.append(f'    label = "{vpc_name}";')
        lines.append(f'    style=filled;')
        lines.append(f'    color=lightblue;')

        # Subnets
        for subnet in elements.get("subnets", []):
            subnet_name = next((tag["Value"] for tag in subnet.get("Tags", []) if tag["Key"] == "Name"), subnet["SubnetId"])
            lines.append(f'    "{subnet["SubnetId"]}" [label="{subnet_name}\\n{subnet["SubnetId"]}"];')

        # Instances
        for instance in elements.get("instances", []):
            lines.append(f'    "{instance["InstanceId"]}" [label="{instance["InstanceId"]}", shape=ellipse, fillcolor=white];')

        # VPC endpoints
        for v in elements.get("vpce", []):
            lines.append(f'    "{v["VpcEndpointId"]}" [label="{v["VpcEndpointId"]}", shape=note, fillcolor=lightyellow];')

        lines.append('  }')  # Cierre del VPC cluster

        # Relaciones simples (puedes enriquecer más si tienes data más precisa)
        for instance in elements.get("instances", []):
            subnet_id = instance.get("SubnetId")
            if subnet_id:
                lines.append(f'  "{subnet_id}" -> "{instance["InstanceId"]}";')

        for v in elements.get("vpce", []):
            subnet_ids = v.get("SubnetIds", [])
            for sid in subnet_ids:
                lines.append(f'  "{sid}" -> "{v["VpcEndpointId"]}";')

        lines.append("}")
        with open(file_path, "w") as f:
            f.write("\n".join(lines))
