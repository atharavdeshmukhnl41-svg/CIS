from neo4j import GraphDatabase
import os
 
from dotenv import load_dotenv
load_dotenv()
 
# ✅ FIXED IMPORT (DO NOT USE azure_collector)
from app.azure_fetcher import AzureFetcher
 
# 🔥 Azure enrichment (UNCHANGED)
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
 
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
 
# -----------------------------------------
# ENRICH VM METADATA (RG + LOCATION)
# -----------------------------------------
def enrich_vm_metadata(session):
 
    try:
        credential = ClientSecretCredential(
            tenant_id=os.getenv("AZURE_TENANT_ID"),
            client_id=os.getenv("AZURE_CLIENT_ID"),
            client_secret=os.getenv("AZURE_CLIENT_SECRET")
        )
 
        compute_client = ComputeManagementClient(
            credential,
            os.getenv("AZURE_SUBSCRIPTION_ID")
        )
 
        for vm in compute_client.virtual_machines.list_all():
 
            vm_name = vm.name
 
            try:
                rg = vm.id.split("/")[4]
            except:
                continue
 
            location = vm.location
 
            session.run("""
            MATCH (v:VM {name:$name})
            SET
                v.resource_group = $rg,
                v.location = $location
            """, {
                "name": vm_name,
                "rg": rg,
                "location": location
            })
 
        print("✅ VM metadata enriched")
 
    except Exception as e:
        print("⚠ Azure enrichment skipped:", str(e))
 
# -----------------------------------------
# MAIN LOAD FUNCTION (NO JSON ANYMORE)
# -----------------------------------------
def load():
 
    # ✅ FIXED USAGE
    collector = AzureFetcher()
    data = collector.get_topology()
 
    print("✅ Topology collected from Azure")
 
    with driver.session() as session:
 
        # Clear old data
        session.run("MATCH (n) DETACH DELETE n")
 
        # -------------------------
        # CREATE NODES
        # -------------------------
        for node in data["nodes"]:
            label = node.pop("label")
            session.run(f"CREATE (n:{label} $props)", props=node)
 
        # -------------------------
        # CREATE RELATIONSHIPS
        # -------------------------
        for edge in data["edges"]:
            session.run(
                f"""
                MATCH (a {{id:$s}})
                MATCH (b {{id:$t}})
                CREATE (a)-[:{edge['type']}]->(b)
                """,
                s=edge["source"],
                t=edge["target"]
            )
 
        print("✅ Topology loaded into Neo4j")
 
        # 🔥 IMPORTANT STEP (UNCHANGED)
        enrich_vm_metadata(session)
 
        print("🚀 Graph ready (dynamic Azure mode)")
 
# -----------------------------------------
# ENTRY
# -----------------------------------------
if __name__ == "__main__":
    load()