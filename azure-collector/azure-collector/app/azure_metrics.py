from azure.mgmt.compute import ComputeManagementClient
from app.azure_auth import get_credentials
from app.config import SUBSCRIPTION_ID
 
 
class AzureMetricsCollector:
 
    def __init__(self):
        credential = get_credentials()
        self.client = ComputeManagementClient(credential, SUBSCRIPTION_ID)
 
    def fetch_metrics(self, vm):
 
        try:
            resource_group = vm.id.split("/")[4]
            vm_name = vm.name
 
            command = {
                "command_id": "RunShellScript",
                "script": [
                    "CPU=$(top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}')",
                    "RX=$(cat /proc/net/dev | awk '/eth0/ {print $2}')",
                    "TX=$(cat /proc/net/dev | awk '/eth0/ {print $10}')",
                    "echo \"$CPU $RX $TX\""
                ]
            }
 
            result = self.client.virtual_machines.begin_run_command(
                resource_group,
                vm_name,
                command
            ).result()
 
            output = result.value[0].message.strip()
            cpu, net_in, net_out = output.split()
 
            return {
                "cpu": float(cpu),
                "network_in": float(net_in),
                "network_out": float(net_out)
            }
 
        except Exception as e:
            print(f"❌ Real-time fetch failed: {e}")
 
            return {
                "cpu": 0,
                "network_in": 0,
                "network_out": 0
            }