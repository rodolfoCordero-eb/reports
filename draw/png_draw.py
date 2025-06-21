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
        graph_attr = {"fontsize": "16"}

        # Construir mapa SubnetId → tipo (public/private)
        subnet_type_map = {}
        route_tables = elements.get("route_tables", [])
        for rt in route_tables:
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

        with Diagram(f"AWS Diagram - {region}", filename=filename, outformat="png", show=False, graph_attr=graph_attr):
            ec2_map = {}
            asg_map = {}
            tg_map = {}
            elb_map = {}

            for vpc in elements.get("vpcs", []):
                vpc_id = vpc["VpcId"]
                with Cluster(f"VPC {vpc_id}"):

                    # Subnets del VPC
                    for subnet in elements.get("subnets", []):
                        if subnet["VpcId"] != vpc_id:
                            continue

                        subnet_id = subnet["SubnetId"]
                        tipo = subnet_type_map.get(subnet_id, "unknown")
                        label = f"{tipo.capitalize()} Subnet {subnet_id}"

                        with Cluster(label):
                            if tipo == "public":
                                _ = PublicSubnet(label)
                            elif tipo == "private":
                                _ = PrivateSubnet(label)
                            else:
                                _ = Blank(label)

                            # EC2 Instances en esta subnet
                            for ec2 in elements.get("instances", []):
                                if ec2.get("SubnetId") == subnet_id:
                                    instance_id = ec2.get("InstanceId")
                                    name = next((t["Value"] for t in ec2.get("Tags", []) if t["Key"] == "Name"), instance_id)
                                    node = EC2(name)
                                    ec2_map[instance_id] = node

                            # ASGs en esta subnet (por VPCZoneIdentifier)
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

                            # RDS en esta subnet
                            for rds in elements.get("dbs", []):
                                subnet_group = rds.get("DBSubnetGroup", {})
                                if any(s["SubnetIdentifier"] == subnet_id for s in subnet_group.get("Subnets", [])):
                                    db_id = rds["DBInstanceIdentifier"]
                                    _ = RDS(db_id)

                            # ELB en esta subnet
                            for lb in elements.get("lbs", []):
                                if subnet_id in lb.get("Subnets", []):
                                    name = lb.get("LoadBalancerName")
                                    elb_node = ELB(name)
                                    elb_map[name] = elb_node

            # Target Groups
            for tg in elements.get("target_groups", []):
                tg_name = tg.get("TargetGroupName", "TG")
                tg_node = Shield(tg_name)
                tg_map[tg["TargetGroupArn"]] = tg_node

            # Conectar ELB -> Target Group
            for listener in elements.get("listeners", []):
                lb_name = listener.get("LoadBalancerName")
                tg_arn = listener.get("DefaultActions", [{}])[0].get("TargetGroupArn")
                if lb_name in elb_map and tg_arn in tg_map:
                    elb_map[lb_name] >> tg_map[tg_arn]

            # Conectar Target Group -> EC2
            for tg in elements.get("target_groups", []):
                tg_arn = tg["TargetGroupArn"]
                for target in tg.get("Targets", []):
                    instance_id = target.get("Id")
                    if instance_id in ec2_map:
                        tg_map[tg_arn] >> ec2_map[instance_id]
