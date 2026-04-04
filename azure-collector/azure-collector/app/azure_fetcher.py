from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from app.config import SUBSCRIPTION_ID
 
class AzureFetcher:
 
    def __init__(self):
        credential = DefaultAzureCredential()
        self.compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)
        self.network_client = NetworkManagementClient(credential, SUBSCRIPTION_ID)
 
    def get_topology(self):
 
        nodes = []
        edges = []
        node_map = {}
 
        vms = list(self.compute_client.virtual_machines.list_all())
        nics = list(self.network_client.network_interfaces.list_all())
        nsgs = list(self.network_client.network_security_groups.list_all())
        public_ips = list(self.network_client.public_ip_addresses.list_all())
        route_tables = list(self.network_client.route_tables.list_all())
        lbs = list(self.network_client.load_balancers.list_all())
        vnets = list(self.network_client.virtual_networks.list_all())
 
        # VM
        for vm in vms:
            nodes.append({
                "id": vm.id,
                "name": vm.name,
                "label": "VM"
            })
 
        # NIC
        for nic in nics:
            nodes.append({
                "id": nic.id,
                "name": nic.name,
                "label": "NIC"
            })
 
        # NIC → SUBNET
        for nic in nics:
            if nic.ip_configurations:
                for ip in nic.ip_configurations:
                    if ip.subnet:
                        edges.append({
                            "source": nic.id,
                            "target": ip.subnet.id,
                            "type": "IN_SUBNET"
                        })
 
        # VM → NIC
        for vm in vms:
            if vm.network_profile:
                for nic in vm.network_profile.network_interfaces:
                    edges.append({
                        "source": vm.id,
                        "target": nic.id,
                        "type": "HAS_NIC"
                    })
 
        # SUBNET nodes
        for vnet in vnets:
            for subnet in vnet.subnets:
                nodes.append({
                    "id": subnet.id,
                    "name": subnet.name,
                    "label": "Subnet"
                })
 
        # NSG
        for nsg in nsgs:
            nodes.append({
                "id": nsg.id,
                "name": nsg.name,
                "label": "NSG"
            })
 
            for rule in nsg.security_rules:
                rule_id = f"{nsg.id}/rule/{rule.name}"
 
                nodes.append({
                    "id": rule_id,
                    "label": "RULE",
                    "port": str(rule.destination_port_range),
                    "access": rule.access.lower(),
                    "priority": int(rule.priority)
                })
 
                edges.append({
                    "source": nsg.id,
                    "target": rule_id,
                    "type": "HAS_RULE"
                })
 
        # NIC → NSG
        for nic in nics:
            if nic.network_security_group:
                edges.append({
                    "source": nic.id,
                    "target": nic.network_security_group.id,
                    "type": "SECURED_BY"
                })
 
        # Public IP
        for pip in public_ips:
            nodes.append({
                "id": pip.id,
                "name": pip.name,
                "label": "PublicIP"
            })
 
            if pip.ip_configuration:
                ref = pip.ip_configuration.id
 
                if "networkInterfaces" in ref:
                    nic_id = ref.split("/ipConfigurations")[0]
                    edges.append({
                        "source": nic_id,
                        "target": pip.id,
                        "type": "HAS_PUBLIC_IP"
                    })
 
                elif "loadBalancers" in ref:
                    lb_id = ref.split("/frontendIPConfigurations")[0]
                    edges.append({
                        "source": lb_id,
                        "target": pip.id,
                        "type": "HAS_PUBLIC_IP"
                    })
 
        # Load Balancer
        for lb in lbs:
            nodes.append({
                "id": lb.id,
                "name": lb.name,
                "label": "LoadBalancer"
            })
 
            for pool in lb.backend_address_pools:
                if pool.backend_ip_configurations:
                    for backend in pool.backend_ip_configurations:
                        nic_id = backend.id.split("/ipConfigurations")[0]
 
                        edges.append({
                            "source": lb.id,
                            "target": nic_id,
                            "type": "BALANCES"
                        })
 
        # Route Tables + Routes
        for rt in route_tables:
            nodes.append({
                "id": rt.id,
                "name": rt.name,
                "label": "RouteTable"
            })
 
            if rt.subnets:
                for subnet in rt.subnets:
                    edges.append({
                        "source": subnet.id,
                        "target": rt.id,
                        "type": "USES_ROUTE_TABLE"
                    })
 
            if rt.routes:
                for route in rt.routes:
                    route_id = f"{rt.id}/route/{route.name}"
 
                    nodes.append({
                        "id": route_id,
                        "label": "Route",
                        "address_prefix": route.address_prefix,
                        "next_hop": str(route.next_hop_type)
                    })
 
                    edges.append({
                        "source": rt.id,
                        "target": route_id,
                        "type": "HAS_ROUTE"
                    })
 
        return {"nodes": nodes, "edges": edges}