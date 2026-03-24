from azure.identity import ClientSecretCredential
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.resource import ResourceManagementClient
from neo4j import GraphDatabase
from datetime import datetime, timedelta
from app.config import AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

class AzureMetricsCollector:
    def __init__(self):
        # Authenticate with Azure
        self.credential = ClientSecretCredential(
            tenant_id=AZURE_TENANT_ID,
            client_id=AZURE_CLIENT_ID,
            client_secret=AZURE_CLIENT_SECRET
        )
        self.subscription_id = AZURE_SUBSCRIPTION_ID
        self.monitor_client = MonitorManagementClient(self.credential, self.subscription_id)
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)

        # Connect to Neo4j
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def fetch_vm_metrics(self, resource_id, metric_names=["Percentage CPU", "Network In Total", "Network Out Total"]):
        timespan = "{}/{}".format(
            (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            datetime.utcnow().isoformat()
        )

        metrics_data = self.monitor_client.metrics.list(
            resource_id,
            timespan=timespan,
            interval='PT5M',
            metricnames=",".join(metric_names),
            aggregation='Average'
        )
        return metrics_data

    def push_metrics_to_neo4j(self, resource_id, metrics_data):
        with self.driver.session() as session:
            for item in metrics_data.value:
                metric_name = item.name.localized_value
                for ts in item.timeseries:
                    for data in ts.data:
                        session.run("""
                            MERGE (r:Resource {id: $resource_id})
                            MERGE (m:Metric {name: $metric_name, timestamp: $timestamp})
                            SET m.average = $average
                            MERGE (r)-[:HAS_METRIC]->(m)
                        """, resource_id=resource_id,
                             metric_name=metric_name,
                             timestamp=data.time_stamp.isoformat(),
                             average=data.average)

    def collect_all_vms_metrics(self):
        # Get all VMs in subscription
        for rg in self.resource_client.resource_groups.list():
            for vm in self.resource_client.resources.list_by_resource_group(rg.name):
                if vm.type == "Microsoft.Compute/virtualMachines":
                    print(f"Collecting metrics for VM: {vm.name}")
                    metrics = self.fetch_vm_metrics(vm.id)
                    self.push_metrics_to_neo4j(vm.id, metrics)

    def close(self):
        self.driver.close()