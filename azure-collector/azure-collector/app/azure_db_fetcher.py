from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
 
from app.config import (
    AZURE_TENANT_ID,
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    SUBSCRIPTION_ID
)
 
 
class AzureDBFetcher:
 
    def __init__(self):
 
        self.credential = ClientSecretCredential(
            tenant_id=AZURE_TENANT_ID,
            client_id=AZURE_CLIENT_ID,
            client_secret=AZURE_CLIENT_SECRET
        )
 
        self.resource_client = ResourceManagementClient(
            self.credential,
            SUBSCRIPTION_ID
        )
 
    # =========================
    # FETCH ALL DATABASES
    # =========================
    def get_databases(self):
 
        dbs = []
 
        for res in self.resource_client.resources.list():
 
            if res.type.lower() in [
                "microsoft.sql/servers/databases",
                "microsoft.dbforpostgresql/servers",
                "microsoft.dbformysql/servers"
            ]:
 
                dbs.append({
                    "id": res.id,
                    "name": res.name,
                    "type": res.type
                })
 
        return dbs