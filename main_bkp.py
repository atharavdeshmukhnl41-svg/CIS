import os
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient

from graph_loader import load_full_graph, close

# Credentials
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")

if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_ID]):
    raise Exception("Missing Azure credentials")

credential = ClientSecretCredential(
    tenant_id=TENANT_ID,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)

compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)
network_client = NetworkManagementClient(credential, SUBSCRIPTION_ID)


# Get subnet from NIC
def get_subnet_from_nic(nic_id):
    try:
        parts = nic_id.split("/")
        resource_group = parts[4]
        nic_name = parts[-1]

        nic = network_client.network_interfaces.get(resource_group, nic_name)

        return nic.ip_configurations[0].subnet.id
    except Exception as e:
        print(f"NIC error: {e}")
        return None


# Get NSG from Subnet
def get_nsg_from_subnet(subnet_id):
    try:
        parts = subnet_id.split("/")
        resource_group = parts[4]
        vnet_name = parts[-3]
        subnet_name = parts[-1]

        subnet = network_client.subnets.get(resource_group, vnet_name, subnet_name)

        if subnet.network_security_group:
            return subnet.network_security_group.id
        return None
    except:
        return None


# Get NSG from NIC (fallback)
def get_nsg_from_nic(nic_id):
    try:
        parts = nic_id.split("/")
        resource_group = parts[4]
        nic_name = parts[-1]

        nic = network_client.network_interfaces.get(resource_group, nic_name)

        if nic.network_security_group:
            return nic.network_security_group.id
        return None
    except:
        return None


# Parse subnet and vnet
def parse_subnet_vnet(subnet_id):
    try:
        parts = subnet_id.split("/")
        subnet_name = parts[-1]
        vnet_name = parts[-3]
        return subnet_name, vnet_name
    except:
        return None, None


# Parse NSG
def parse_nsg(nsg_id):
    if nsg_id:
        return nsg_id.split("/")[-1]
    return None


# Build graph data
full_data = []

print("\nProcessing Azure resources...\n")

for vm in compute_client.virtual_machines.list_all():
    try:
        if not vm.network_profile or not vm.network_profile.network_interfaces:
            continue

        vm_name = vm.name
        location = vm.location

        nic_id = vm.network_profile.network_interfaces[0].id

        subnet_id = get_subnet_from_nic(nic_id)
        if not subnet_id:
            continue

        subnet_name, vnet_name = parse_subnet_vnet(subnet_id)

        # Check NSG (subnet first, then NIC)
        nsg_id = get_nsg_from_subnet(subnet_id)
        if not nsg_id:
            nsg_id = get_nsg_from_nic(nic_id)

        nsg_name = parse_nsg(nsg_id)

        full_data.append({
            "vm": vm_name,
            "location": location,
            "subnet": subnet_name,
            "vnet": vnet_name,
            "nsg": nsg_name
        })

        print(f"{vm_name} → {subnet_name} → {vnet_name} → NSG: {nsg_name}")

    except Exception as e:
        print(f"Error processing VM: {e}")


print("\nLoading into Neo4j...\n")

load_full_graph(full_data)
close()

print("\nGraph created successfully!")