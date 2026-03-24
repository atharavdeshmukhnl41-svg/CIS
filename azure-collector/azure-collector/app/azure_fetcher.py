from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
import os


class AzureFetcher:
    def __init__(self):
        credential = DefaultAzureCredential()
        subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")

        self.compute_client = ComputeManagementClient(
            credential, subscription_id
        )

        self.network_client = NetworkManagementClient(
            credential, subscription_id
        )

    # ---------------- VMs ----------------
    def get_vms(self):
        vms = []

        for vm in self.compute_client.virtual_machines.list_all():
            vm.resource_group = vm.id.split("/")[4]   
            vms.append(vm)

        return vms

    # ---------------- NICs ----------------
    def get_nics(self):
        return list(self.network_client.network_interfaces.list_all())

    # ---------------- VNets ----------------
    def get_vnets(self):
        return list(self.network_client.virtual_networks.list_all())

    # ---------------- NSGs ----------------
    def get_nsgs(self):
        return list(self.network_client.network_security_groups.list_all())

    # ---------------- Public IPs ----------------
    def get_public_ips(self):
        return list(self.network_client.public_ip_addresses.list_all())

    def get_route_tables(self):
        return list(self.network_client.route_tables.list_all())