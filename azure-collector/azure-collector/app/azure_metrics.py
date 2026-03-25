from azure.identity import ClientSecretCredential
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.resource import ResourceManagementClient
from neo4j import GraphDatabase
from datetime import datetime, timedelta
 
from app.config import (
    AZURE_TENANT_ID,
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    SUBSCRIPTION_ID,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD
)
 
 
class AzureMetricsCollector:
 
    def __init__(self):
 
        self.credential = ClientSecretCredential(
            tenant_id=AZURE_TENANT_ID,
            client_id=AZURE_CLIENT_ID,
            client_secret=AZURE_CLIENT_SECRET
        )
 
        self.monitor_client = MonitorManagementClient(
            self.credential,
            SUBSCRIPTION_ID
        )
 
        self.resource_client = ResourceManagementClient(
            self.credential,
            SUBSCRIPTION_ID
        )
 
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
 
    # =========================
    # SAFE: GET VM RESOURCE ID
    # =========================
    def get_vm_resource_id(self, vm_name):
 
        for res in self.resource_client.resources.list():
            if (
                res.name.lower() == vm_name.lower()
                and res.type.lower() == "microsoft.compute/virtualmachines"
            ):
                return res.id
 
        return None
 
    # =========================
    # SAFE: FETCH METRICS
    # =========================
    def fetch_metrics(self, resource_id):
 
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
 
        metrics_data = self.monitor_client.metrics.list(
            resource_id,
            timespan=f"{start_time}/{end_time}",
            interval="PT1M",
            metricnames="Percentage CPU,Network In Total,Network Out Total"
        )
 
        result = {
            "cpu": 0,
            "network_in": 0,
            "network_out": 0
        }
 
        for item in metrics_data.value:
            for ts in item.timeseries:
                for data in ts.data:
                    if data.average is not None:
 
                        if item.name.value == "Percentage CPU":
                            result["cpu"] = round(data.average, 2)
 
                        elif item.name.value == "Network In Total":
                            result["network_in"] = round(data.average, 2)
 
                        elif item.name.value == "Network Out Total":
                            result["network_out"] = round(data.average, 2)
 
        return result
 
    # =========================
    # SAFE: STORE ONLY METRICS
    # =========================
    def store_metrics(self, vm_name, metrics):
 
        with self.driver.session() as session:
 
            session.run("""
            MATCH (vm:VM {name:$vm})
 
            MERGE (m:Metric {vm:$vm})
 
            SET m.cpu = $cpu,
                m.network_in = $net_in,
                m.network_out = $net_out,
                m.timestamp = datetime()
 
            MERGE (vm)-[:HAS_METRIC]->(m)
            """,
            vm=vm_name,
            cpu=metrics["cpu"],
            net_in=metrics["network_in"],
            net_out=metrics["network_out"]
            )
 
    # =========================
    # NEW METHOD ONLY (NO BREAK)
    # =========================
    def collect_and_store(self, vm_name):
 
        resource_id = self.get_vm_resource_id(vm_name)
 
        if not resource_id:
            print("❌ VM not found in Azure")
            return None
 
        metrics = self.fetch_metrics(resource_id)
 
        self.store_metrics(vm_name, metrics)
 
        return metrics   # IMPORTANT (used by run_metrics)
 
    def close(self):
        self.driver.close()
