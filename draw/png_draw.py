from diagrams import Diagram, Cluster, Node
from diagrams.aws.network import VPC, PrivateSubnet, PublicSubnet, InternetGateway, NATGateway
from diagrams.aws.compute import EC2, EC2AutoScaling,EC2ImageBuilder
from diagrams.aws.database import RDS
from diagrams.aws.network import Endpoint, VpnConnection, TransitGateway
from diagrams.aws.network import ELB
import os
from .draw_strategy import DrawStrategy

class png_draw(DrawStrategy):

    def name(self):
        return self.__class__.__name__
    

    def draw(self, elements, path, region):
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, f"{region}.png")

        # Nombre del VPC
        vpc_name = "VPC"
        if elements.get("vpcs"):
            vpc = elements["vpcs"][0]
            vpc_name = next((tag["Value"] for tag in vpc.get("Tags", []) if tag["Key"] == "Name"), vpc["VpcId"])

        # Clasificación de subnets
        public_subnets = []
        private_subnets = []

        for sn in elements.get("subnets", []):
            name = next((tag["Value"] for tag in sn.get("Tags", []) if tag["Key"] == "Name"), sn["SubnetId"])
            if sn.get("MapPublicIpOnLaunch"):
                public_subnets.append((name, sn["SubnetId"]))
            else:
                private_subnets.append((name, sn["SubnetId"]))

        # Agrupar instancias por subnet
        instances_by_subnet = {}
        for inst in elements.get("instances", []):
            subnet_id = inst.get("SubnetId")
            if subnet_id:
                instances_by_subnet.setdefault(subnet_id, []).append(inst)

        # Obtener instancias administradas por ASG
        asg_instance_ids = set()
        for asg in elements.get("asg", []):
            asg_instance_ids.update(i["InstanceId"] for i in asg.get("Instances", []))

        with Diagram(f"AWS Network - {region}", filename=file_path, outformat="png", show=False, direction="TB"):
            with Cluster(vpc_name):
                igw = InternetGateway("IGW")
                nat = NATGateway("NAT Gateway")

                # Subnets públicas
                for name, subnet_id in public_subnets:
                    with Cluster(f"Public Subnet\n{name}"):
                        for inst in instances_by_subnet.get(subnet_id, []):
                            if inst["InstanceId"] in asg_instance_ids:
                                continue  # Ya será dibujada desde el ASG
                            ec2_node = EC2(inst["InstanceId"])
                            igw >> ec2_node

                # Subnets privadas
                for name, subnet_id in private_subnets:
                    with Cluster(f"Private Subnet\n{name}"):
                        for inst in instances_by_subnet.get(subnet_id, []):
                            if inst["InstanceId"] in asg_instance_ids:
                                continue  # Ya será dibujada desde el ASG
                            ec2_node = EC2(inst["InstanceId"])
                            nat >> ec2_node

            # Auto Scaling Groups
            if elements.get("asg"):
                with Cluster("Auto Scaling Groups"):
                    for group in elements["asg"]:
                        group_name = group["AutoScalingGroupName"]
                        asg_node = EC2AutoScaling(group_name)
                        lt = group.get("LaunchTemplate")
                        lc_name = group.get("LaunchConfigurationName")

                        if lt:
                            lt_name = lt.get("LaunchTemplateName", "LaunchTemplate")
                            lt_node =  EC2ImageBuilder(lt_name)
                            lt_node >> asg_node
                        elif lc_name:
                            lc_node = EC2ImageBuilder(lc_name)
                            lc_node >> asg_node
                        ec2_node = EC2(f"Instances")
                        asg_node >> ec2_node


                        # Instancias del ASG
                       # for inst in:
                       #     
                       #     asg_node >> ec2_node

            # Load Balancers
            if elements.get("lbs"):
                with Cluster("Load Balancers"):
                    for lb in elements["lbs"]:
                        ELB(lb["LoadBalancerName"])

            # RDS
            if elements.get("dbs"):
                with Cluster("Databases"):
                    for db in elements["dbs"]:
                        RDS(db["DBInstanceIdentifier"])

            # VPC Endpoints
            if elements.get("vpce"):
                with Cluster("Endpoints"):
                    for ep in elements["vpce"]:
                        name = ep.get("VpcEndpointId", ep.get("ServiceName", "VPCE"))
                        Endpoint(name)

            # VPC Peerings
            if elements.get("peerings"):
                with Cluster("VPC Peerings"):
                    for p in elements["peerings"]:
                        TransitGateway(p["VpcPeeringConnectionId"])

            # Transit Gateways
            if elements.get("tgw"):
                with Cluster("Transit Gateways"):
                    for t in elements["tgw"]:
                        TransitGateway(t["TransitGatewayId"])

            # VPN Connections
            if elements.get("vpns"):
                with Cluster("VPN Connections"):
                    for v in elements["vpns"]:
                        VpnConnection(v["VpnConnectionId"])