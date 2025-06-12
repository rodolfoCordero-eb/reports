from .action_strategy import ActionStrategy
import boto3
import pandas as pd
class null_action(ActionStrategy):
    def name(self):
        return self.__class__.__name__

    def run(self,session,acc_id, acc_name):
        sts_client = boto3.client("sts")
        identity = sts_client.get_caller_identity()
        userId=identity["UserId"]
        account = identity["Account"]
        print(f"\n👤 UserId: {userId}")
        print(f"\n🧾 AccountId: {account}")
        df = pd.DataFrame({ 'UserId':[userId],
                           'AccountId':[account]
        })
        return df 