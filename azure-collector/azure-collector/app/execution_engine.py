from app.azure_client import compute_client, network_client
from app.topology_resolver import TopologyResolver

class ExecutionEngine:

    def __init__(self):
        self.resolver = TopologyResolver()

    # -------------------------
    # MAIN EXECUTION
    # -------------------------
    def execute(self, action, vm=None, port=None):

        try:
            # ✅ VALIDATION (CRITICAL FIX)
            if not vm:
                return {
                    "status": "error",
                    "message": "VM name missing"
                }

            # Check if Azure clients are available
            if compute_client is None or network_client is None:
                return {
                    "status": "error",
                    "message": "Azure credentials not configured - cannot execute actions"
                }

            # 🔥 Resolve RG
            resource_group = self.resolver.get_vm_resource_group(vm)

            if not resource_group:
                return {
                    "status": "error",
                    "message": f"Resource group not found for VM {vm}"
                }

            # -------------------------
            # ACTION HANDLING
            # -------------------------
            if action == "restart_vm":
                return self.restart_vm(vm, resource_group)

            elif action == "fix_nsg":

                if not port:
                    return {
                        "status": "error",
                        "message": "Port required for NSG fix"
                    }

                return self.fix_nsg(vm, port, resource_group)

            return {
                "status": "unknown",
                "message": "No action mapped"
            }
    
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
 
    # -------------------------
    # RESTART VM
    # -------------------------
    def restart_vm(self, vm, resource_group):
    
        compute_client.virtual_machines.begin_restart(
            resource_group,
            vm
        ).result()  # wait for completion
    
        return {
            "status": "success",
            "message": f"VM {vm} restarted in RG {resource_group}"
        }
 
    # -------------------------
    # FIX NSG
    # -------------------------
    def fix_nsg(self, vm, port, resource_group):
 
        # 🔥 Get NSG from graph (NOT assumption)
        nsg_name = self.resolver.get_nsg_for_vm(vm)
 
        if not nsg_name:
            return {
                "status": "error",
                "message": "NSG not found in topology"
            }
 
        network_client.security_rules.begin_create_or_update(
            resource_group,
            nsg_name,
            f"allow-{port}",
            {
                "protocol": "Tcp",
                "access": "Allow",
                "direction": "Inbound",
                "priority": 100,
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "source_port_range": "*",
                "destination_port_range": str(port),
            }
        )
 
        return {
            "status": "success",
            "message": f"NSG {nsg_name} updated for port {port}"
        }