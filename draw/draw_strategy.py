from abc import ABC,abstractmethod
import os 
from tabulate import tabulate

class DrawStrategy(ABC):

    @abstractmethod
    def name(self):
        pass

    @abstractmethod    
    def draw(self,elements,path, region):
        pass
    
    def run(self,session,acc_id, acc_name,path,region=None):
        regions = session.get_available_regions("ec2") if not region else [region] 
        for region in regions:
            elements=[]
            ec2 = session.client("ec2",region_name=region)
            rds = session.client("rds",region_name=region)
            asg = session.client("autoscaling", region_name=region)
            tg= session.client("elbv2", region_name=region)
            elements = self._collect_elements(session,ec2,asg,rds,tg,region)
            tmp_path = os.path.join(path, f"{acc_name}-{acc_id}")
            self.draw(elements,tmp_path,region)

    def _collect_elements(self, session, ec2,asg, rds,tg, region):
        elements = {}

        def safe_get(client_call, label, key):
            try:
                return client_call().get(key, [])
            except Exception as e:
                print(f"[{region}] Failed to describe {label}: {e}")
                return []

        # ELB
        try:
            elb = session.client("elbv2", region_name=region)
            elements["lbs"] = safe_get(elb.describe_load_balancers, "load balancers", "LoadBalancers")
        except Exception as e:
            print(f"[{region}] Failed to initialize ELB client: {e}")
            elements["lbs"] = []

        # EC2 resources
        elements["instances"] = safe_get(lambda: ec2.describe_instances(), "instances", "Reservations")
        elements["instances"] = [
            i for r in elements["instances"] for i in r.get("Instances", [])
        ] if elements["instances"] else []

        elements["vpce"] = safe_get(ec2.describe_vpc_endpoints, "VPC endpoints", "VpcEndpoints")
        elements["peerings"] = safe_get(ec2.describe_vpc_peering_connections, "VPC peerings", "VpcPeeringConnections")
        elements["tgw"] = safe_get(ec2.describe_transit_gateways, "transit gateways", "TransitGateways")
        elements["vpns"] = safe_get(ec2.describe_vpn_connections, "VPN connections", "VpnConnections")
        elements["vpcs"] = safe_get(ec2.describe_vpcs, "VPCs", "Vpcs")
        elements["subnets"] = safe_get(ec2.describe_subnets, "subnets", "Subnets")
        elements["route_tables"] = safe_get(ec2.describe_route_tables,"routetables","RouteTables")
        # RDS
        elements["dbs"] = safe_get(rds.describe_db_instances, "RDS instances", "DBInstances")

        #ASG 
        #elements['asg'] = safe_get(lambda: asg.describe_auto_scaling_groups(), "AutoScalingGroups", [])
        #elements['launch_configs'] = safe_get(lambda: asg.describe_launch_configurations(), "LaunchConfigurations", [])
        #elements['launch_templates'] = safe_get(lambda: ec2.describe_launch_templates(), "LaunchTemplates", [])

        elements['asg'] = asg.describe_auto_scaling_groups().get("AutoScalingGroups", [])
        elements['launch_configs'] = asg.describe_launch_configurations().get("LaunchConfigurations", [])
        elements['launch_templates'] = ec2.describe_launch_templates().get("LaunchTemplates", [])

        elements['tg']= tg.describe_target_groups()

        # Optional: summary
        try:
            self.print_element_summary(elements,region)
        except Exception as e:
            print(f"[{region}] Failed to print element summary: {e}")

        return elements

    def print_element_summary(self,elements,region):
        summary = []
        keys_to_count = [
            ("instances", "EC2 Instances"),
            ("dbs", "RDS Instances"),
            ("vpce", "VPC Endpoints"),
            ("lbs", "Load Balancers"),
            ("peerings", "VPC Peerings"),
            ("tgw", "Transit Gateways"),
            ("vpns", "VPN Connections"),
            ("vpcs", "VPCs"),
            ("subnets", "Subnets"),
            ("asg", "Auto Scaling Groups"),
            ("launch_configs", "Launch Config"),
            ("launch_templates", "Launch Template"),
            ("tg", "Target Group"),
            ("route_tables", "Route Tables")
        ]

        for key, label in keys_to_count:
            count = len(elements.get(key, []))
            summary.append((label, count))
        print(f"\nElements: {region}")
        print(tabulate(summary, headers=["Element", "Count"], tablefmt="fancy_grid"))

