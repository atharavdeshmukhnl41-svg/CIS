from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from app.config import SUBSCRIPTION_ID
 
 
class AzureFetcher:
 
    def __init__(self):
        credential = DefaultAzureCredential()
 
        self.compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)
        self.network_client = NetworkManagementClient(credential, SUBSCRIPTION_ID)
 
    def get_vms(self):
        vms = []
 
        for vm in self.compute_client.virtual_machines.list_all():
 
            power_state = "unknown"
 
            try:
                rg = vm.id.split("/")[4]
 
                instance = self.compute_client.virtual_machines.instance_view(
                    rg,
                    vm.name
                )
 
                for status in instance.statuses:
                    if "PowerState/" in status.code:
                        power_state = status.display_status
 
            except Exception as e:
                print("Power state fetch failed:", vm.name, e)
 
            vm.power_state = power_state
            vms.append(vm)
 
        return vms
 
    def get_nics(self):
        return list(self.network_client.network_interfaces.list_all())

    def get_subnets(self):
        subnets = []
        for vnet in self.network_client.virtual_networks.list_all():
            for subnet in vnet.subnets:
                subnets.append(subnet)
        return subnets
 
    def get_vnets(self):
        return list(self.network_client.virtual_networks.list_all())
 
    def get_nsgs(self):
        return list(self.network_client.network_security_groups.list_all())
 
    def get_public_ips(self):
        return list(self.network_client.public_ip_addresses.list_all())
 
    def get_route_tables(self):
        return list(self.network_client.route_tables.list_all())
 
    def get_load_balancers(self):
        lbs = list(self.network_client.load_balancers.list_all())
    
        print("DEBUG LB COUNT:", len(lbs))
    
        return lbs

    def get_nat_gateways(self):
        return list(self.network_client.nat_gateways.list_all())

