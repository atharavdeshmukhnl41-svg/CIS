import os
from dotenv import load_dotenv
 
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
 
load_dotenv()
 
# ✅ Load from environment
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
 
# 🔥 VALIDATION (important)
if not SUBSCRIPTION_ID:
    raise Exception("AZURE_SUBSCRIPTION_ID not set")
 
credential = ClientSecretCredential(
    tenant_id=TENANT_ID,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)
 
compute_client = ComputeManagementClient(
    credential,
    SUBSCRIPTION_ID
)
 
network_client = NetworkManagementClient(
    credential,
    SUBSCRIPTION_ID
)