import boto3
from botocore.exceptions import ClientError
from single import Single
import os

class Session:
    def __init__(self):
        self.ROLE_NAME="OrganizationAccountAccessRole"
        self.session_default = boto3.Session()
        self.acc_id=self.session_default.client("sts").get_caller_identity()["Account"]
        self.org_client = boto3.client("organizations")
        self.sts_client = boto3.client("sts")
        self.list_accounts()

    def assume_role(self,account_id, role_name):
        try:
            if account_id == self.acc_id:
                return self.session_default
            response = self.sts_client.assume_role(
                RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
                RoleSessionName="OrgAuditSession"
            )
            creds = response["Credentials"]
            return boto3.Session(
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
            )
        except ClientError as e:
            print(f"[{account_id}] ❌ Failed to assume role: {e}")
            return None

    def list_accounts(self):
        accounts = []
        paginator = self.org_client.get_paginator("list_accounts")
        for page in paginator.paginate():
            accounts.extend(page["Accounts"])
        self.accounts = [acc for acc in accounts if acc["Status"] == "ACTIVE"]
    
    def execute(self,strategy,region=None):
        print("\n\n----------------------------------")
        print(f"👓 {strategy.name()} Draw")
        for acc in self.accounts:
            acc_id = acc["Id"]
            acc_name = acc["Name"]
            session  =self.assume_role(acc_id,self.ROLE_NAME)
            if (session):
                single=Single(session=session,name=acc_name)
                single.execute(strategy,region)

   