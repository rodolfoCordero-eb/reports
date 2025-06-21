
from lxml import etree
import os
from .draw_strategy import DrawStrategy
class drawio_draw(DrawStrategy):
    def name(self):
        return self.__class__.__name__

    def draw(self, elements, path, region):
        filename = os.path.join(path, f"{region}.drawio")

        mxfile = etree.Element("mxfile", host="app.diagrams.net")
        diagram = etree.SubElement(mxfile, "diagram", name=region)
        root = etree.Element("mxGraphModel")
        root.set("dx", "1600")
        root.set("dy", "1600")
        root.set("grid", "1")
        root.set("gridSize", "10")
        root.set("guides", "1")
        root.set("tooltips", "1")
        root.set("connect", "1")
        root.set("arrows", "1")
        root.set("fold", "1")
        root.set("page", "1")
        root.set("pageScale", "1")
        root.set("pageWidth", "827")
        root.set("pageHeight", "1169")
        root.set("math", "0")
        root.set("shadow", "0")

        root_cell = etree.SubElement(root, "root")
        etree.SubElement(root_cell, "mxCell", id="0")
        etree.SubElement(root_cell, "mxCell", id="1", parent="0")

        shape_map = {}

        def add_shape(id_counter, name, style, x, y, width=160, height=80):
            cell = etree.Element("mxCell", id=str(id_counter), value=name, style=style,
                                 vertex="1", parent="1")
            geometry = etree.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(width), height=str(height))
            geometry.set("as", "geometry")
            root_cell.append(cell)
            return cell

        def add_edge(source_id, target_id):
            if source_id is None or target_id is None:
                return
            edge_id = f"e{source_id}_{target_id}"
            edge = etree.Element("mxCell", id=edge_id, edge="1", source=str(source_id), target=str(target_id), parent="1")
            geometry = etree.SubElement(edge, "mxGeometry")
            geometry.set("as", "geometry")
            root_cell.append(edge)

        y_pub = 40
        y_priv = 400
        x_offset = 40
        spacing_subnet = 250
        spacing_resource = 70

        subnet_type_map = {}
        for rt in elements.get("route_tables", []):
            for assoc in rt.get("Associations", []):
                subnet_id = assoc.get("SubnetId")
                if not subnet_id:
                    continue
                for route in rt.get("Routes", []):
                    if route.get("GatewayId", "").startswith("igw-"):
                        subnet_type_map[subnet_id] = "public"
                        break
                else:
                    subnet_type_map[subnet_id] = "private"

        id_counter = 2

        # Primero subnets públicas
        pub_subnets = [s for s in elements.get("subnets", []) if subnet_type_map.get(s["SubnetId"], "private") == "public"]
        priv_subnets = [s for s in elements.get("subnets", []) if subnet_type_map.get(s["SubnetId"], "private") == "private"]

        # Función para dibujar recursos en subnet
        def draw_resources(subnet, x, y_start):
            nonlocal id_counter
            subnet_id = subnet["SubnetId"]
            subnet_label = f"{subnet_type_map.get(subnet_id, 'Private').capitalize()} Subnet\n{subnet_id}"
            subnet_style = "shape=swimlane;fillColor=#DAE8FC;strokeColor=#6C8EBF;rounded=1;fontSize=12;"
            subnet_cell_id = id_counter
            add_shape(id_counter, subnet_label, subnet_style, x, y_start, 180, 260)
            shape_map[subnet_id] = id_counter
            id_counter += 1

            y = y_start + 20
            # EC2
            for ec2 in elements.get("instances", []):
                if ec2.get("SubnetId") == subnet_id:
                    name = next((t["Value"] for t in ec2.get("Tags", []) if t["Key"] == "Name"), ec2["InstanceId"])
                    style = "shape=mxgraph.aws4.compute.ec2_instance"
                    add_shape(id_counter, name, style, x + 10, y)
                    shape_map[ec2["InstanceId"]] = id_counter
                    add_edge(subnet_cell_id, id_counter)
                    id_counter += 1
                    y += spacing_resource

            # RDS
            for rds in elements.get("dbs", []):
                for sub in rds.get("DBSubnetGroup", {}).get("Subnets", []):
                    if sub.get("SubnetIdentifier") == subnet_id:
                        name = rds["DBInstanceIdentifier"]
                        style = "shape=mxgraph.aws4.database.rds_instance"
                        add_shape(id_counter, name, style, x + 10, y)
                        shape_map[rds["DBInstanceIdentifier"]] = id_counter
                        add_edge(subnet_cell_id, id_counter)
                        id_counter += 1
                        y += spacing_resource

            # ASG
            for asg in elements.get("asg", []):
                subnet_ids = asg.get("VPCZoneIdentifier", "").split(',')
                if subnet_id in subnet_ids:
                    name = asg["AutoScalingGroupName"]
                    count = len(asg.get("Instances", []))
                    label = f"{name}\n{count} EC2"
                    style = "shape=mxgraph.aws4.compute.auto_scaling"
                    add_shape(id_counter, label, style, x + 10, y)
                    shape_map[name] = id_counter
                    add_edge(subnet_cell_id, id_counter)
                    for inst in asg.get("Instances", []):
                        inst_id = inst.get("InstanceId")
                        if inst_id in shape_map:
                            add_edge(id_counter, shape_map[inst_id])
                    id_counter += 1
                    y += spacing_resource

            # ELB
            for lb in elements.get("lbs", []):
                if subnet_id in lb.get("Subnets", []):
                    name = lb.get("LoadBalancerName")
                    style = "shape=mxgraph.aws4.network.elb"
                    add_shape(id_counter, name, style, x + 10, y)
                    shape_map[name] = id_counter
                    for target in elements.get("instances", []):
                        if target.get("SubnetId") == subnet_id:
                            add_edge(id_counter, shape_map.get(target.get("InstanceId")))
                    for asg in elements.get("asg", []):
                        if subnet_id in asg.get("VPCZoneIdentifier", "").split(','):
                            add_edge(id_counter, shape_map.get(asg["AutoScalingGroupName"]))
                    id_counter += 1
                    y += spacing_resource

            # NAT Gateway
            for nat in elements.get("nat_gateways", []):
                if nat.get("SubnetId") == subnet_id:
                    name = nat.get("NatGatewayId")
                    style = "shape=mxgraph.aws4.network.nat_gateway"
                    add_shape(id_counter, name, style, x + 10, y)
                    add_edge(subnet_cell_id, id_counter)
                    id_counter += 1
                    y += spacing_resource

            # IGW
            for igw in elements.get("internet_gateways", []):
                for att in igw.get("Attachments", []):
                    if att.get("VpcId") == subnet.get("VpcId"):
                        name = igw["InternetGatewayId"]
                        style = "shape=mxgraph.aws4.network.internet_gateway"
                        add_shape(id_counter, name, style, x + 10, y)
                        add_edge(id_counter, subnet_cell_id)
                        id_counter += 1
                        y += spacing_resource

        # Dibuja subnets públicas
        for i, subnet in enumerate(pub_subnets):
            x = x_offset + i * spacing_subnet
            draw_resources(subnet, x, y_pub)

        # Dibuja subnets privadas
        for i, subnet in enumerate(priv_subnets):
            x = x_offset + i * spacing_subnet
            draw_resources(subnet, x, y_priv)

        diagram.append(root)
        mxfile_string = etree.tostring(mxfile, pretty_print=True, encoding="unicode")

        with open(filename, "w") as f:
            f.write(mxfile_string)