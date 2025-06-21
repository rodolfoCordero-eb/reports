from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, AutoScaling
from diagrams.aws.network import ELB, VPC, Endpoint, NATGateway
from diagrams.aws.database import RDS
from diagrams.aws.security import Shield
from diagrams.aws.management import Cloudwatch
from diagrams.aws.network import TransitGateway, VpnConnection, PrivateSubnet, PublicSubnet
from diagrams.aws.compute import EC2ImageBuilder
from diagrams.generic.blank import Blank

import os
from .draw_strategy import DrawStrategy

class png_draw(DrawStrategy):

    def name(self):
        return self.__class__.__name__
    def draw(self, elements, path, region):
        filename = os.path.join(path, f"{region}.png")
        graph_attr = {
            "fontsize": "18",
            "splines": "ortho",
            "rankdir": "LR",
            "nodesep": "1.2",
            "ranksep": "1.4"
        }

        with Diagram(f"AWS Diagram - {region}", filename=filename, outformat="png", show=False, graph_attr=graph_attr):
            ec2_map = {}
            asg_map = {}
            tg_map = {}
            elb_map = {}
            subnet_nodes = {}
            vpc_gateways = {}

            subnet_type_map = {}
            igw_nodes = {}
            nat_nodes = {}
            tgw_nodes = {}
            vpn_nodes = {}

            for rt in elements.get("route_tables", []):
                routes = rt.get("Routes", [])
                associations = rt.get("Associations", [])
                for assoc in associations:
                    subnet_id = assoc.get("SubnetId")
                    if not subnet_id:
                        continue
                    for r in routes:
                        gw = r.get("GatewayId", "")
                        if gw.startswith("igw-"):
                            subnet_type_map[subnet_id] = "public"
                            break
                    else:
                        subnet_type_map.setdefault(subnet_id, "private")

            for vpc in elements.get("vpcs", []):
                vpc_id = vpc["VpcId"]
                with Cluster(f"VPC {vpc_id}"):
                    for igw in elements.get("internet_gateways", []):
                        if any(attach.get("VpcId") == vpc_id for attach in igw.get("Attachments", [])):
                            igw_node = InternetGateway(igw["InternetGatewayId"])
                            igw_nodes[vpc_id] = igw_node

                    for nat in elements.get("nat_gateways", []):
                        if nat.get("VpcId") == vpc_id:
                            nat_node = NATGateway(nat["NatGatewayId"])
                            nat_nodes[nat["NatGatewayId"]] = nat_node

                    for tgw in elements.get("tgw", []):
                        tgw_node = TransitGateway(tgw["TransitGatewayId"])
                        tgw_nodes[tgw["TransitGatewayId"]] = tgw_node

                    for vpn in elements.get("vpns", []):
                        vpn_node = VPNConnection(vpn["VpnConnectionId"])
                        vpn_nodes[vpn["VpnConnectionId"]] = vpn_node

                    sorted_subnets = sorted(
                        [s for s in elements.get("subnets", []) if s["VpcId"] == vpc_id],
                        key=lambda s: 0 if subnet_type_map.get(s["SubnetId"], "private") == "public" else 1
                    )

                    for subnet in sorted_subnets:
                        subnet_id = subnet["SubnetId"]
                        tipo = subnet_type_map.get(subnet_id, "unknown")
                        label = f"{tipo.capitalize()} Subnet {subnet_id}"
                        with Cluster(label):
                            if tipo == "public":
                                subnet_node = PublicSubnet(label)
                            elif tipo == "private":
                                subnet_node = PrivateSubnet(label)
                            else:
                                subnet_node = Blank(label)

                            subnet_nodes[subnet_id] = subnet_node

                            vertical_group = []

                            for ec2 in elements.get("instances", []):
                                if ec2.get("SubnetId") == subnet_id:
                                    instance_id = ec2.get("InstanceId")
                                    name = next((t["Value"] for t in ec2.get("Tags", []) if t["Key"] == "Name"), instance_id)
                                    node = EC2(name)
                                    ec2_map[instance_id] = node
                                    vertical_group.append(node)

                            for asg in elements.get("asg", []):
                                subnet_ids = [s.strip() for s in asg.get("VPCZoneIdentifier", "").split(",") if s.strip()]
                                if subnet_id in subnet_ids:
                                    asg_name = asg["AutoScalingGroupName"]
                                    instance_count = len(asg.get("Instances", []))
                                    label = f"{asg_name}\n{instance_count} EC2"
                                    node = AutoScaling(label)
                                    asg_map[asg_name] = node
                                    lt = asg.get("LaunchTemplate")
                                    lc_name = asg.get("LaunchConfigurationName")
                                    if lt:
                                        lt_label = lt.get("LaunchTemplateName", "LaunchTemplate")
                                        lt_node = EC2ImageBuilder(lt_label)
                                        node >> lt_node
                                    elif lc_name:
                                        lc_node = Blank(f"LaunchConfig: {lc_name}")
                                        node >> lc_node
                                    vertical_group.append(node)

                            for rds in elements.get("dbs", []):
                                subnet_group = rds.get("DBSubnetGroup", {})
                                if any(s["SubnetIdentifier"] == subnet_id for s in subnet_group.get("Subnets", [])):
                                    db_id = rds["DBInstanceIdentifier"]
                                    db_node = RDS(db_id)
                                    vertical_group.append(db_node)

                            for lb in elements.get("lbs", []):
                                if subnet_id in lb.get("Subnets", []):
                                    name = lb.get("LoadBalancerName")
                                    elb_node = ELB(name)
                                    elb_map[name] = elb_node
                                    vertical_group.append(elb_node)

            for tg in elements.get("target_groups", []):
                tg_name = tg.get("TargetGroupName", "TG")
                tg_node = Shield(tg_name)
                tg_map[tg["TargetGroupArn"]] = tg_node

            for listener in elements.get("listeners", []):
                lb_name = listener.get("LoadBalancerName")
                tg_arn = listener.get("DefaultActions", [{}])[0].get("TargetGroupArn")
                if lb_name in elb_map and tg_arn in tg_map:
                    elb_map[lb_name] >> tg_map[tg_arn]

            for tg in elements.get("target_groups", []):
                tg_arn = tg["TargetGroupArn"]
                for target in tg.get("Targets", []):
                    instance_id = target.get("Id")
                    if instance_id in ec2_map:
                        tg_map[tg_arn] >> ec2_map[instance_id]

            for asg in elements.get("asg", []):
                asg_name = asg["AutoScalingGroupName"]
                tg_arns = asg.get("TargetGroupARNs", [])
                if asg_name in asg_map:
                    for tg_arn in tg_arns:
                        if tg_arn in tg_map:
                            tg_map[tg_arn] >> asg_map[asg_name]

            for rt in elements.get("route_tables", []):
                routes = rt.get("Routes", [])
                associations = rt.get("Associations", [])
                for assoc in associations:
                    subnet_id = assoc.get("SubnetId")
                    if not subnet_id:
                        continue
                    for r in routes:
                        gw_id = r.get("GatewayId", "")
                        nat_id = r.get("NatGatewayId", "")
                        tgw_id = r.get("TransitGatewayId", "")
                        vpn_id = r.get("VpnGatewayId", "")

                        if gw_id.startswith("igw-") and subnet_id in subnet_nodes:
                            vpc_id = next((igw["VpcId"] for igw in elements.get("internet_gateways", []) if igw["InternetGatewayId"] == gw_id), None)
                            if vpc_id in igw_nodes:
                                subnet_nodes[subnet_id] >> igw_nodes[vpc_id]

                        if nat_id and subnet_id in subnet_nodes:
                            if nat_id in nat_nodes:
                                subnet_nodes[subnet_id] >> nat_nodes[nat_id]

                        if tgw_id and tgw_id in tgw_nodes and subnet_id in subnet_nodes:
                            subnet_nodes[subnet_id] >> tgw_nodes[tgw_id]

                        if vpn_id and vpn_id in vpn_nodes and subnet_id in subnet_nodes:
                            subnet_nodes[subnet_id] >> vpn_nodes[vpn_id]
