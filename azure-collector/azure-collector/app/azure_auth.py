from azure.identity import ClientSecretCredential
from app.config import *

def get_credential():
    return ClientSecretCredential(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET
    )