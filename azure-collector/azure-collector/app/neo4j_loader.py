from neo4j import GraphDatabase
from app.config import *
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
import os
 
class Neo4jLoader:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
 
        # 🔥 Azure Auth
        credential = ClientSecretCredential(
            tenant_id=os.getenv("AZURE_TENANT_ID"),
            client_id=os.getenv("AZURE_CLIENT_ID"),
            client_secret=os.getenv("AZURE_CLIENT_SECRET")
        )
 
        self.compute_client = ComputeManagementClient(
            credential,
            SUBSCRIPTION_ID
        )
    def load_topology(self, topology):
 
        with self.driver.session() as session:
 
            # Clear old data
            session.run("MATCH (n) DETACH DELETE n")
 
            # -------------------------
            # CREATE NODES
            # -------------------------
            for node in topology["nodes"]:
 
                props = {
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "label": node.get("label")
                }
 
                # Extra props
                if "port" in node:
                    props["port"] = str(node["port"])
 
                if "access" in node:
                    props["access"] = node["access"]
 
                if "priority" in node:
                    props["priority"] = int(node["priority"])
 
                query = f"""
                CREATE (n:{node['label']} $props)
                """
 
                session.run(query, props=props)
 
            # -------------------------
            # CREATE RELATIONSHIPS
            # -------------------------
            for edge in topology["edges"]:
                session.run(
                    f"""
                    MATCH (a {{id:$source}})
                    MATCH (b {{id:$target}})
                    CREATE (a)-[:{edge['type']}]->(b)
                    """,
                    source=edge["source"],
                    target=edge["target"]
                )
 
        print("✅ Topology loaded")
 
    # -----------------------------------------
    # 🔥 NEW: ENRICH VM WITH AZURE DATA
    # -----------------------------------------
    def enrich_vm_metadata(self):
 
        with self.driver.session() as session:
 
            for vm in self.compute_client.virtual_machines.list_all():
 
                vm_name = vm.name
 
                # 🔥 Extract RG from Azure ID
                try:
                    rg = vm.id.split("/")[4]
                except:
                    continue
 
                location = vm.location
                power_state = None
 
                try:
                    instance_view = self.compute_client.virtual_machines.instance_view(rg, vm_name)
                    statuses = getattr(instance_view, "statuses", []) or []
                    for status in statuses:
                        code = getattr(status, "code", "")
                        if isinstance(code, str) and code.lower().startswith("powerstate/"):
                            power_state = code.split("/")[-1]
                            break
                except Exception:
                    power_state = None
 
                session.run("""
                MATCH (v:VM {name:$name})
                SET
                    v.resource_group = $rg,
                    v.location = $location,
                    v.power_state = $power_state
                """, {
                    "name": vm_name,
                    "rg": rg,
                    "location": location,
                    "power_state": power_state
                })
 
        print("✅ VM metadata enriched (RG + location + power_state)")
 
    def close(self):
        self.driver.close()
 
    # -----------------------------------------
    # INSERT METRICS
    # -----------------------------------------
    def insert_metrics(self, vm, cpu, net_in, net_out):
 
        query = """
        CREATE (m:Metrics {
            vm: $vm,
            cpu: $cpu,
            network_in: $net_in,
            network_out: $net_out,
            timestamp: datetime()
        })
        """
 
        with self.driver.session() as session:
            session.run(query, {
                "vm": vm,
                "cpu": cpu,
                "net_in": net_in,
                "net_out": net_out
            })
 
        print("📊 Metrics stored in Neo4j")