import boto3
import pandas as pd
from botocore.exceptions import ClientError
import os
from openpyxl import load_workbook

class Single:
    def __init__(self):
        self.org_client = boto3.client("organizations")
        self.sts_client = boto3.client("sts")
        self.set_caller_identity()
        self.file_paths="./excel_files"
        pass

    def set_caller_identity(self):
        self.identity = self.sts_client.get_caller_identity()
        userId=self.identity["UserId"]
        account = self.identity["Account"]
        print(f"\n👤 UserId: {userId}")
        print(f"\n🧾 AccountId: {account}")
        return self.identity
    
    def execute(self,strategy):
        print("\n\n----------------------------------")
        print(f"👓 {strategy.name()}")
        file_name = f"{self.file_paths}/{strategy.name()}.xlsx"
        if not os.path.exists(file_name):
            print("📗 Creating book")
            df = pd.DataFrame({"Module":[strategy.name()]})
            with pd.ExcelWriter(file_name,engine='openpyxl') as writer:
                df.to_excel(writer,sheet_name="Index",index=False)
        session  = boto3.Session()            
        if (session):
            acc_id = self.set_caller_identity()["UserId"]
            acc_name = self.set_caller_identity()["Account"]
            print(f"🔍 Scanning account {acc_id} ({acc_name})...")
            result = strategy.run(session,acc_id, acc_name)
            if not result.empty:
                book = load_workbook(file_name)
                if acc_name in book.sheetnames:
                    print(f"🗡️ Remove book {acc_name}")
                    std = book[acc_name]
                    book.remove(std)
                    book.save(file_name)
                print(f"\n📁 Writing File {strategy.name()} with {acc_name} content")
                with pd.ExcelWriter(file_name,engine='openpyxl', mode = 'a') as writer:
                    result.to_excel(writer,sheet_name=acc_name,index=False)
        print("----------------------------------\n\n")
