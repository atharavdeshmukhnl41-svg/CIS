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
    # VMs
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
 
    def get_nsgs(self):
        return list(self.network_client.network_security_groups.list_all())
 
    def get_public_ips(self):
        return list(self.network_client.public_ip_addresses.list_all())
 
    def get_route_tables(self):
        return list(self.network_client.route_tables.list_all())
 
    def get_load_balancers(self):
        return list(self.network_client.load_balancers.list_all())
 
    # -----------------------------------------
    # 🔥 FINAL TOPOLOGY (FULLY FIXED)
    # -----------------------------------------
    def get_topology(self):
 
        nodes = []
        edges = []
        node_map = {}
 
        vms = self.get_vms()
        nics = self.get_nics()
        nsgs = self.get_nsgs()
        public_ips = self.get_public_ips()
        route_tables = self.get_route_tables()
        lbs = self.get_load_balancers()
 
        # -------------------------
        # VM NODES
        # -------------------------
        for vm in vms:
            node_map[vm.id] = vm.id
 
            nodes.append({
                "id": vm.id,
                "name": vm.name,
                "label": "VM",
                "power_state": getattr(vm, "power_state", "unknown")
            })
 
        # -------------------------
        # NIC NODES
        # -------------------------
        for nic in nics:
            node_map[nic.id] = nic.id
 
            nodes.append({
                "id": nic.id,
                "name": nic.name,
                "label": "NIC"
            })
 
        # -------------------------
        # VM → NIC (CORRECT)
        # -------------------------
        for vm in vms:
 
            if not vm.network_profile:
                continue
 
            for nic_ref in vm.network_profile.network_interfaces:
 
                edges.append({
                    "source": vm.id,
                    "target": nic_ref.id,
                    "type": "HAS_NIC"
                })
 
                print("✅ LINK VM->NIC:", vm.name, "→", nic_ref.id)
 
        # -------------------------
        # NSG NODES + LINKS
        # -------------------------
        for nic in nics:
 
            if nic.network_security_group:
 
                nsg = nic.network_security_group
 
                if nsg.id not in node_map:
                    node_map[nsg.id] = nsg.id
 
                    nodes.append({
                        "id": nsg.id,
                        "name": nsg.id.split("/")[-1],
                        "label": "NSG"
                    })
 
                edges.append({
                    "source": nic.id,
                    "target": nsg.id,
                    "type": "SECURED_BY"
                })
 
        # -------------------------
        # NSG RULES
        # -------------------------
        for nsg in nsgs:
 
            if nsg.id not in node_map:
                continue
 
            for rule in nsg.security_rules:
 
                rule_id = f"{nsg.id}/rule/{rule.name}"
 
                nodes.append({
                    "id": rule_id,
                    "name": rule.name,
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
 
        # -------------------------
        # PUBLIC IP (FIXED LOGIC)
        # -------------------------
        for pip in public_ips:
 
            node_map[pip.id] = pip.id
 
            nodes.append({
                "id": pip.id,
                "name": pip.name,
                "label": "PublicIP"
            })
 
            if pip.ip_configuration and pip.ip_configuration.id:
 
                ip_id = pip.ip_configuration.id
 
                # NIC case
                if "networkInterfaces" in ip_id:
                    nic_id = ip_id.split("/ipConfigurations")[0]
 
                    edges.append({
                        "source": nic_id,
                        "target": pip.id,
                        "type": "HAS_PUBLIC_IP"
                    })
 
                    print("✅ LINK NIC->PIP:", nic_id, "→", pip.name)
 
                # Load Balancer case
                elif "loadBalancers" in ip_id:
                    lb_id = ip_id.split("/frontendIPConfigurations")[0]
 
                    edges.append({
                        "source": lb_id,
                        "target": pip.id,
                        "type": "HAS_PUBLIC_IP"
                    })
 
                    print("✅ LINK LB->PIP:", lb_id, "→", pip.name)
 
        # -------------------------
        # LOAD BALANCER → NIC
        # -------------------------
        for lb in lbs:
 
            node_map[lb.id] = lb.id
 
            nodes.append({
                "id": lb.id,
                "name": lb.name,
                "label": "LoadBalancer"
            })
 
            for pool in lb.backend_address_pools:
 
                if not pool.backend_ip_configurations:
                    continue
 
                for backend in pool.backend_ip_configurations:
 
                    nic_id = backend.id.split("/ipConfigurations")[0]
 
                    edges.append({
                        "source": lb.id,
                        "target": nic_id,
                        "type": "BALANCES"
                    })
 
                    print("✅ LINK LB->NIC:", lb.name, "→", nic_id)
 
        # -------------------------
        # ROUTE TABLE
        # -------------------------
        for rt in route_tables:
 
            node_map[rt.id] = rt.id
 
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
 
                    print("✅ LINK SUBNET->RT:", subnet.id, "→", rt.name)
 
        return {
            "nodes": nodes,
            "edges": edges
        }