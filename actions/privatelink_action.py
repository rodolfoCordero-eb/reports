from .action_strategy import ActionStrategy
import boto3
import pandas as pd

class privatelink_action(ActionStrategy):
    def name(self):
        return self.__class__.__name__

    def run(self,session, acc_id, acc_name):
        ec2_client = session.client("ec2")
        
        endpoints_data = []
        services_data = []

        # --- PrivateLink ENDPOINTS (consumidos) ---
        try:
            paginator = ec2_client.get_paginator("describe_vpc_endpoints")
            for page in paginator.paginate():
                for ep in page.get("VpcEndpoints", []):
                    if ep.get("VpcEndpointType") != "Interface":
                        continue  # Solo PrivateLink

                    endpoints_data.append({
                        "AccountId": acc_id,
                        "AccountName": acc_name,
                        "Type": "Endpoint",
                        "VpcEndpointId": ep.get("VpcEndpointId"),
                        "ServiceName": ep.get("ServiceName"),
                        "VpcId": ep.get("VpcId"),
                        "State": ep.get("State"),
                        "PrivateDnsEnabled": ep.get("PrivateDnsEnabled", False),
                        "SubnetIds": ", ".join(ep.get("SubnetIds", [])),
                        "SecurityGroupIds": ", ".join(
                            [group["GroupId"] for group in ep.get("Groups", [])]
                        ),
                        "CreationTimestamp": ep.get("CreationTimestamp").isoformat() if ep.get("CreationTimestamp") else None,
                        "Tags": {tag['Key']: tag['Value'] for tag in ep.get("Tags", [])}
                    })
        except Exception as e:
            print(f"[ERROR] Fetching VPC endpoints in {acc_name} ({acc_id}): {e}")

        # --- PrivateLink SERVICES (publicados) ---
        try:
            paginator = ec2_client.get_paginator("describe_vpc_endpoint_service_configurations")
            for page in paginator.paginate():
                for svc in page.get("ServiceConfigurations", []):
                    services_data.append({
                        "AccountId": acc_id,
                        "AccountName": acc_name,
                        "Type": "Service",
                        "ServiceName": svc.get("ServiceName"),
                        "ServiceId": svc.get("ServiceId"),
                        "AcceptanceRequired": svc.get("AcceptanceRequired"),
                        "NetworkLoadBalancerArns": ", ".join(svc.get("NetworkLoadBalancerArns", [])),
                        "GatewayLoadBalancerArns": ", ".join(svc.get("GatewayLoadBalancerArns", [])),
                        "AvailabilityZones": ", ".join(svc.get("AvailabilityZones", [])),
                        "ManagesVpcEndpoints": svc.get("ManagesVpcEndpoints", False),
                        "PrivateDnsName": svc.get("PrivateDnsName"),
                        "ServiceState": svc.get("ServiceState"),
                        "CreationTimestamp": svc.get("CreationTimestamp").isoformat() if svc.get("CreationTimestamp") else None,
                        "Tags": {tag['Key']: tag['Value'] for tag in svc.get("Tags", [])}
                    })
        except Exception as e:
            print(f"[ERROR] Fetching VPC endpoint services in {acc_name} ({acc_id}): {e}")

        # Convertir a DataFrames y unirlos
        df_endpoints = pd.DataFrame(endpoints_data)
        df_services = pd.DataFrame(services_data)
        
        # Unimos ambos si hay datos, o devolvemos uno solo si el otro está vacío
        if not df_endpoints.empty and not df_services.empty:
            return pd.concat([df_endpoints, df_services], ignore_index=True)
        elif not df_endpoints.empty:
            return df_endpoints
        elif not df_services.empty:
            return df_services
        else:
            return pd.DataFrame()  # Vacío si no hay datos
