from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from app.config import SUBSCRIPTION_ID
 
class AzureFetcher:
 
    def __init__(self):
        credential = DefaultAzureCredential()
        self.compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)
        self.network_client = NetworkManagementClient(credential, SUBSCRIPTION_ID)
 
    def parse_resource_id(self, resource_id):
        if not resource_id:
            return {}
        parts = resource_id.strip('/').split('/')
        return {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}
 
    def get_subnet(self, subnet_id):
        info = self.parse_resource_id(subnet_id)
        if not info:
            return None
        return self.network_client.subnets.get(
            info.get('resourceGroups'),
            info.get('virtualNetworks'),
            info.get('subnets')
        )
 
    def get_route_table(self, route_table_id):
        info = self.parse_resource_id(route_table_id)
        if not info:
            return None
        return self.network_client.route_tables.get(
            info.get('resourceGroups'),
            info.get('routeTables')
        )
 
    def get_topology(self):
 
        nodes = []
        edges = []
        node_map = {}

        def build_resource_node(resource, label, type_hint):
            info = self.parse_resource_id(getattr(resource, "id", ""))
            return {
                "id": getattr(resource, "id", None),
                "name": getattr(resource, "name", None),
                "label": label,
                "resource_group": info.get("resourceGroups", "Unknown"),
                "location": getattr(resource, "location", "Unknown"),
                "state": getattr(resource, "provisioning_state", "Unknown") or "Unknown",
                "type": getattr(resource, "type", type_hint)
            }
 
        vms = list(self.compute_client.virtual_machines.list_all())
        nics = list(self.network_client.network_interfaces.list_all())
        nsgs = list(self.network_client.network_security_groups.list_all())
        public_ips = list(self.network_client.public_ip_addresses.list_all())
        route_tables = list(self.network_client.route_tables.list_all())
        lbs = list(self.network_client.load_balancers.list_all())
        vnets = list(self.network_client.virtual_networks.list_all())
 
        # VM
        for vm in vms:
            nodes.append(build_resource_node(vm, "VM", "Microsoft.Compute/virtualMachines"))
 
        # NIC
        for nic in nics:
            nodes.append(build_resource_node(nic, "NIC", "Microsoft.Network/networkInterfaces"))
 
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
                subnet_info = self.parse_resource_id(subnet.id)
                nodes.append({
                    "id": subnet.id,
                    "name": subnet.name,
                    "label": "Subnet",
                    "resource_group": subnet_info.get("resourceGroups", "Unknown"),
                    "location": vnet.location,
                    "state": getattr(subnet, "provisioning_state", "Unknown") or "Unknown",
                    "type": "Microsoft.Network/virtualNetworks/subnets"
                })
 
        # NSG
        for nsg in nsgs:
            nodes.append(build_resource_node(nsg, "NSG", "Microsoft.Network/networkSecurityGroups"))
 
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
            nodes.append(build_resource_node(pip, "PublicIP", "Microsoft.Network/publicIPAddresses"))
 
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
            nodes.append(build_resource_node(lb, "LoadBalancer", "Microsoft.Network/loadBalancers"))
 
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
            nodes.append(build_resource_node(rt, "RouteTable", "Microsoft.Network/routeTables"))
 
            if rt.subnets:
                for subnet in rt.subnets:
                    edges.append({
                        "source": rt.id,
                        "target": subnet.id,
                        "type": "ASSOCIATED_WITH"
                    })
 
            if rt.routes:
                for route in rt.routes:
                    route_id = f"{rt.id}/route/{route.name}"
                    route_info = self.parse_resource_id(route_id)
 
                    nodes.append({
                        "id": route_id,
                        "name": route.name,
                        "label": "Route",
                        "resource_group": route_info.get("resourceGroups", "Unknown"),
                        "location": getattr(rt, "location", "Unknown"),
                        "state": "Unknown",
                        "type": "Microsoft.Network/routeTables/routes",
                        "address_prefix": route.address_prefix,
                        "next_hop": str(route.next_hop_type)
                    })
 
                    edges.append({
                        "source": rt.id,
                        "target": route_id,
                        "type": "HAS_ROUTE"
                    })
 
        return {"nodes": nodes, "edges": edges}