import os
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ElasticLoadBalancing, VPCPeering, TransitGateway, VpnGateway
from diagrams.generic.network import Firewall
from .draw_strategy import DrawStrategy

class png_draw(DrawStrategy):

    def name(self):
        return self.__class__.__name__
    
    def run(self,session, acc_id, acc_name, path="./images"):
        regions = session.get_available_regions("ec2")

        for region in regions:
            reg_sess = session._session.create_client("ec2", region_name=region)
            rds_client = session._session.create_client("rds", region_name=region)

            try:
                elb_client = session._session.create_client("elbv2", region_name=region)
                lbs = elb_client.describe_load_balancers().get("LoadBalancers", [])
            except:
                lbs = []

            instances = [i for r in reg_sess.describe_instances().get("Reservations", []) for i in r.get("Instances", [])]
            vpce = reg_sess.describe_vpc_endpoints().get("VpcEndpoints", [])
            dbs = rds_client.describe_db_instances().get("DBInstances", [])
            peerings = reg_sess.describe_vpc_peering_connections().get("VpcPeeringConnections", [])
            tgw = reg_sess.describe_transit_gateways().get("TransitGateways", [])
            vpns = reg_sess.describe_vpn_connections().get("VpnConnections", [])

            out_dir = os.path.join(path, f"{acc_name}-{acc_id}")
            os.makedirs(out_dir, exist_ok=True)
            filename = os.path.join(out_dir, f"{region}_diagram")

            with Diagram(f"{acc_name} - {region}", filename=filename, outformat="png"):
                with Cluster(f"Resources in {region}"):
                    for i in instances:
                        EC2(i["InstanceId"])
                    for v in vpce:
                        Firewall(v["VpcEndpointId"])  # genérico para VPCE
                    for d in dbs:
                        RDS(d["DBInstanceIdentifier"])
                    for l in lbs:
                        ElasticLoadBalancing(l["LoadBalancerName"])
                    for p in peerings:
                        VPCPeering(p["VpcPeeringConnectionId"])
                    for g in tgw:
                        TransitGateway(g["TransitGatewayId"])
                    for vpn in vpns:
                        VpnGateway(vpn["VpnConnectionId"])