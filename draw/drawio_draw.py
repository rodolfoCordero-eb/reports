import os
import boto3
from .draw_strategy import DrawStrategy
class drawio_draw(DrawStrategy):
    def name(self):
        return self.__class__.__name__
    def run(self,session, acc_id, acc_name, path="./images"):
        regions = session.get_available_regions("ec2")

        for region in regions:
            reg_sess = boto3.Session(profile_name=session.profile_name, region_name=region)
            ec2 = reg_sess.client("ec2")
            rds = reg_sess.client("rds")

            try:
                elb = reg_sess.client("elbv2")
                lbs = elb.describe_load_balancers().get("LoadBalancers", [])
            except:
                lbs = []

            instances = [i for r in ec2.describe_instances().get("Reservations", []) for i in r.get("Instances", [])]
            vpce = ec2.describe_vpc_endpoints().get("VpcEndpoints", [])
            dbs = rds.describe_db_instances().get("DBInstances", [])
            peerings = ec2.describe_vpc_peering_connections().get("VpcPeeringConnections", [])
            tgw = ec2.describe_transit_gateways().get("TransitGateways", [])
            vpns = ec2.describe_vpn_connections().get("VpnConnections", [])

            nodes = []
            x, y = 40, 40
            node_id = 10

            def node(label, x, y):
                nonlocal node_id
                id_ = str(node_id)
                node_id += 1
                return f'<mxCell id="{id_}" value="{label}" style="shape=swimlane;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="120" height="60" as="geometry"/></mxCell>'

            for i in instances:
                nodes.append(node(f"EC2: {i['InstanceId']}", x, y)); y += 80
            for e in vpce:
                nodes.append(node(f"VPCE: {e['VpcEndpointId']}", x, y)); y += 80
            for d in dbs:
                nodes.append(node(f"RDS: {d['DBInstanceIdentifier']}", x, y)); y += 80
            for l in lbs:
                nodes.append(node(f"LB: {l['LoadBalancerName']}", x, y)); y += 80
            for p in peerings:
                nodes.append(node(f"Peering: {p['VpcPeeringConnectionId']}", x, y)); y += 80
            for g in tgw:
                nodes.append(node(f"TGW: {g['TransitGatewayId']}", x, y)); y += 80
            for vpn in vpns:
                nodes.append(node(f"VPN: {vpn['VpnConnectionId']}", x, y)); y += 80

            xml = f"""<mxGraphModel dx='1270' dy='894' grid='1' gridSize='10'>
            <root>
                <mxCell id='0'/>
                <mxCell id='1' parent='0'/>
                {''.join(nodes)}
            </root>
            </mxGraphModel>"""

            out_dir = os.path.join(path, f"{acc_name}-{acc_id}")
            os.makedirs(out_dir, exist_ok=True)
            filename = os.path.join(out_dir, f"{region}.drawio")
            with open(filename, "w") as f:
                print(f"\n📁 Writing File {filename} with {acc_name} content")
                f.write(xml)
