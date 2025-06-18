from .action_strategy import ActionStrategy
import boto3
import pandas as pd
class networkinterconnection_action(ActionStrategy):
    def name(self):
        return self.__class__.__name__

    def run(self,session,acc_id, acc_name):
        data = []

        # Get all regions
        ec2 = session.client('ec2')
        regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]

        for region in regions:
            try:
                ec2 = session.client('ec2', region_name=region)

                # -- VPC Peering Connections --
                peering_conns = ec2.describe_vpc_peering_connections()['VpcPeeringConnections']
                for pc in peering_conns:
                    data.append({
                        'AccountId': acc_id,
                        'AccountName': acc_name,
                        'Region': region,
                        'Type': 'VPC Peering',
                        'Id': pc['VpcPeeringConnectionId'],
                        'State': pc['Status']['Code'],
                        'Detail': f"{pc['RequesterVpcInfo'].get('VpcId')} ↔ {pc['AccepterVpcInfo'].get('VpcId')}"
                    })

                # -- VPN Tunnels --
                vpn_conns = ec2.describe_vpn_connections()['VpnConnections']
                for vpn in vpn_conns:
                    for tunnel in vpn.get('Options', {}).get('TunnelOptions', [{}]):
                        data.append({
                            'AccountId': acc_id,
                            'AccountName': acc_name,
                            'Region': region,
                            'Type': 'VPN Tunnel',
                            'Id': vpn['VpnConnectionId'],
                            'State': vpn['State'],
                            'Detail': f"Tunnel: {tunnel.get('OutsideIpAddress', 'N/A')}"
                        })

                # -- Transit Gateway Attachments --
                try:
                    tgw = session.client('ec2', region_name=region)
                    tgw_attachments = tgw.describe_transit_gateway_attachments()['TransitGatewayAttachments']
                    for attach in tgw_attachments:
                        data.append({
                            'AccountId': acc_id,
                            'AccountName': acc_name,
                            'Region': region,
                            'Type': 'TransitGatewayAttachment',
                            'Id': attach['TransitGatewayAttachmentId'],
                            'State': attach['State'],
                            'Detail': f"{attach['ResourceType']} → {attach.get('ResourceId')}"
                        })
                except Exception as tgw_err:
                    print(f"⚠️ No Transit Gateway in {region}: {tgw_err}")

                # -- VPC Endpoints (PrivateLink) --
                endpoints = ec2.describe_vpc_endpoints()['VpcEndpoints']
                for ep in endpoints:
                    data.append({
                        'AccountId': acc_id,
                        'AccountName': acc_name,
                        'Region': region,
                        'Type': 'PrivateLink',
                        'Id': ep['VpcEndpointId'],
                        'State': ep['State'],
                        'Detail': ep['ServiceName']
                    })

            except Exception as e:
                print(f"⚠️ Error in region {region}: {e}")

        return pd.DataFrame(data)