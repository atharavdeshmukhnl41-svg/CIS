from azure.identity import DefaultAzureCredential
 
 
def get_credentials():
    """
    Returns Azure credential object.
    Works with:
    - az login
    - environment variables
    - managed identity (future)
    """
    return DefaultAzureCredential()