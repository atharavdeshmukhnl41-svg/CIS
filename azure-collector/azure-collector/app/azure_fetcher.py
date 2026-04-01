from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from app.config import SUBSCRIPTION_ID
 
 
class AzureFetcher:
 
    def __init__(self):
        credential = DefaultAzureCredential()
 
        self.compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)
        self.network_client = NetworkManagementClient(credential, SUBSCRIPTION_ID)
 
    # -----------------------------------------
    # EXISTING METHODS (UNCHANGED)
    # -----------------------------------------
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
 
    # -----------------------------------------
    # 🔥 NEW: TOPOLOGY BUILDER (CRITICAL FIX)
    # -----------------------------------------
    def get_topology(self):
 
        nodes = []
        edges = []
 
        node_id = 1
        node_map = {}  # prevents duplicates
 
        vms = self.get_vms()
        nics = self.get_nics()
        nsgs = self.get_nsgs()
 
        # -------------------------
        # VM NODES
        # -------------------------
        for vm in vms:
            node_map[vm.id] = node_id
 
            nodes.append({
                "id": node_id,
                "name": vm.name,
                "label": "VM",
                "power_state": getattr(vm, "power_state", "unknown")
            })
 
            node_id += 1
 
        # -------------------------
        # NIC NODES + VM LINKS
        # -------------------------
        for nic in nics:
 
            if nic.id not in node_map:
                node_map[nic.id] = node_id
 
                nodes.append({
                    "id": node_id,
                    "name": nic.name,
                    "label": "NIC"
                })
 
                node_id += 1
 
            nic_id = node_map[nic.id]
 
            # Attach to VM
            if nic.virtual_machine:
                vm_id = node_map.get(nic.virtual_machine.id)
 
                if vm_id:
                    edges.append({
                        "source": vm_id,
                        "target": nic_id,
                        "type": "HAS_NIC"
                    })
 
            # -------------------------
            # NSG LINK
            # -------------------------
            if nic.network_security_group:
 
                nsg = nic.network_security_group
 
                if nsg.id not in node_map:
                    node_map[nsg.id] = node_id
 
                    nodes.append({
                        "id": node_id,
                        "name": nsg.id.split("/")[-1],
                        "label": "NSG"
                    })
 
                    node_id += 1
 
                nsg_id = node_map[nsg.id]
 
                edges.append({
                    "source": nic_id,
                    "target": nsg_id,
                    "type": "SECURED_BY"
                })
 
        # -------------------------
        # NSG RULES (🔥 PRIORITY FIX)
        # -------------------------
        for nsg in nsgs:
 
            nsg_id = node_map.get(nsg.id)
 
            if not nsg_id:
                continue
 
            for rule in nsg.security_rules:
 
                rule_node_id = node_id
 
                nodes.append({
                    "id": rule_node_id,
                    "name": rule.name,
                    "label": "RULE",
                    "port": str(rule.destination_port_range),
                    "access": rule.access.lower(),
                    "priority": int(rule.priority)
                })
 
                edges.append({
                    "source": nsg_id,
                    "target": rule_node_id,
                    "type": "HAS_RULE"
                })
 
                node_id += 1
 
        return {
            "nodes": nodes,
            "edges": edges
        }