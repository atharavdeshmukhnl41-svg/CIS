from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
import os


class LBFetcher:
    def __init__(self):
        credential = DefaultAzureCredential()
        subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID") or os.environ.get("SUBSCRIPTION_ID")

        self.network_client = NetworkManagementClient(
            credential, subscription_id
        )

    def get_load_balancers(self):
        return list(self.network_client.load_balancers.list_all())