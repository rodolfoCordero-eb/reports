from .action_strategy import ActionStrategy
import boto3
import pandas as pd
class vpc_action(ActionStrategy):
    def name(self):
        return self.__class__.__name__

    def run(self,session,acc_id, acc_name):
        data = []

        # Get available regions for EC2
        ec2_client = session.client('ec2')
        regions = [r['RegionName'] for r in ec2_client.describe_regions()['Regions']]

        for region in regions:
            try:
                ec2 = session.client('ec2', region_name=region)

                # Get all VPCs
                vpcs = ec2.describe_vpcs()['Vpcs']
                vpc_map = {vpc['VpcId']: vpc['CidrBlock'] for vpc in vpcs}

                # Get all route tables
                route_tables = ec2.describe_route_tables()['RouteTables']
                public_subnet_ids = set()

                # Identify public subnets based on route tables
                for rt in route_tables:
                    for route in rt.get('Routes', []):
                        if route.get('GatewayId', '').startswith('igw-'):
                            for assoc in rt.get('Associations', []):
                                if 'SubnetId' in assoc:
                                    public_subnet_ids.add(assoc['SubnetId'])

                # Get all subnets
                subnets = ec2.describe_subnets()['Subnets']
                for subnet in subnets:
                    subnet_id = subnet['SubnetId']
                    subnet_cidr = subnet['CidrBlock']
                    vpc_id = subnet['VpcId']
                    subnet_type = 'Public' if subnet_id in public_subnet_ids else 'Private'

                    data.append({
                        'AccountId': acc_id,
                        'AccountName': acc_name,
                        'Region': region,
                        'VPCId': vpc_id,
                        'VPC_CIDR': vpc_map.get(vpc_id, ''),
                        'SubnetId': subnet_id,
                        'Subnet_CIDR': subnet_cidr,
                        'SubnetType': subnet_type
                    })

            except Exception as e:
                print(f"⚠️ Error in region {region}: {e}")

        return pd.DataFrame(data)