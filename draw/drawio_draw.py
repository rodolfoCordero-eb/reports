import xml.etree.ElementTree as ET
from abc import ABC
from uuid import uuid4
import os
from .draw_strategy import DrawStrategy
class drawio_draw(DrawStrategy):
    def name(self):
        return self.__class__.__name__

    def draw(self, elements, path, region):
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, f"{region}.drawio")

        def make_id():
            return str(uuid4()).replace("-", "")

        mxfile = ET.Element("mxfile", host="app.diagrams.net")
        diagram = ET.SubElement(mxfile, "diagram", name=region)
        root = ET.Element("mxGraphModel")
        diagram.append(root)

        root_node = ET.SubElement(root, "root")
        ET.SubElement(root_node, "mxCell", id="0")
        ET.SubElement(root_node, "mxCell", id="1", parent="0")

        spacing_x = 300
        spacing_y = 120
        y_offset = 0

        def add_node(label, x, y, parent="1", style="shape=rectangle", width=120, height=60):
            node_id = make_id()
            cell = ET.SubElement(root_node, "mxCell", {
                "id": node_id,
                "value": label,
                "style": style,
                "vertex": "1",
                "parent": parent
            })
            ET.SubElement(cell, "mxGeometry", {
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
                "as": "geometry"
            })
            return node_id

        def add_edge(source, target):
            edge_id = make_id()
            cell = ET.SubElement(root_node, "mxCell", {
                "id": edge_id,
                "style": "endArrow=block;edgeStyle=orthogonalEdgeStyle",
                "edge": "1",
                "source": source,
                "target": target,
                "parent": "1"
            })
            ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})

        # Map de recursos: ID de recurso a nodo drawio
        ec2_nodes = {}
        subnet_nodes = {}
        vpc_nodes = {}
        asg_nodes = {}
        rds_nodes = {}
        elb_nodes = {}

        # Obtener IDs de instancias dentro de ASG para no duplicar
        asg_instance_ids = set()
        for asg in elements.get("asg", []):
            asg_instance_ids.update(i["InstanceId"] for i in asg.get("Instances", []))

        # 1. Dibujar VPCs
        vpc_y = y_offset
        for vpc in elements.get("vpcs", []):
            vpc_id = vpc.get("VpcId", "VPC")
            node_id = add_node(vpc_id, spacing_x * 5, vpc_y, style="shape=mxgraph.aws2025.networking_amazon_vpc")
            vpc_nodes[vpc_id] = node_id
            vpc_y += spacing_y

        # 2. Dibujar Subnets
        subnet_y = y_offset
        for subnet in elements.get("subnets", []):
            subnet_id = subnet.get("SubnetId", "Subnet")
            node_id = add_node(subnet_id, spacing_x * 4, subnet_y, style="shape=mxgraph.aws2025.networking_amazon_vpc_subnet")
            subnet_nodes[subnet_id] = node_id
            subnet_y += spacing_y

        # 3. Dibujar EC2 (fuera ASG)
        ec2_y = y_offset
        for i in elements.get("instances", []):
            if i["InstanceId"] not in asg_instance_ids:
                label = next((tag["Value"] for tag in i.get("Tags", []) if tag["Key"] == "Name"), i["InstanceId"])
                node_id = add_node(label, spacing_x * 0, ec2_y, style="shape=mxgraph.aws2025.compute.amazon_ec2")
                ec2_nodes[i["InstanceId"]] = node_id
                ec2_y += spacing_y

        # 4. Dibujar ASGs
        asg_y = y_offset
        for asg in elements.get("asg", []):
            group_name = asg.get("AutoScalingGroupName", "ASG")
            node_id = add_node(group_name, spacing_x * 1, asg_y, style="shape=mxgraph.aws2025.compute.auto_scaling")
            asg_nodes[group_name] = node_id

            # Launch Template o Config
            lt = asg.get("LaunchTemplate")
            lc_name = asg.get("LaunchConfigurationName")

            if lt:
                lt_name = lt.get("LaunchTemplateName", "LaunchTemplate")
                lt_node = add_node(lt_name, spacing_x * 1 - 150, asg_y, style="shape=mxgraph.aws2025.compute.launch_template")
                add_edge(lt_node, node_id)
            elif lc
