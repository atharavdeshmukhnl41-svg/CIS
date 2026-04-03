from neo4j import GraphDatabase

import os

 

from dotenv import load_dotenv

load_dotenv()

 

from app.azure_fetcher import AzureFetcher

 

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

                SET v.resource_group = $rg,

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

# MAIN LOAD FUNCTION (FIXED)

# -----------------------------------------

def load():

 

    collector = AzureFetcher()

    data = collector.get_topology()

 

    print("✅ Topology collected from Azure")

 

    with driver.session() as session:

 

        # -------------------------

        # CLEAR GRAPH

        # -------------------------

        session.run("MATCH (n) DETACH DELETE n")

 

        # -------------------------

        # CREATE NODES (FIXED)

        # -------------------------

        for node in data["nodes"]:
        
            if "id" not in node:
                print("❌ Node missing ID:", node)
                continue
        
            label = node.get("label")
            props = node.copy()
            props.pop("label", None)
        
            session.run(
                f"""
                MERGE (n:{label} {{id:$id}})
                SET n += $props
                """,
                id=props["id"],
                props=props
            )
        
        print("✅ Nodes created with stable IDs")
        
        
        # -------------------------
        # CREATE RELATIONSHIPS (STRICT)
        # -------------------------
        for edge in data["edges"]:
        
            source = edge.get("source")
            target = edge.get("target")
        
            if source is None or target is None:
                print("❌ Edge missing source/target:", edge)
                continue
        
            result = session.run(
                f"""
                MATCH (a {{id:$source}})
                MATCH (b {{id:$target}})
                MERGE (a)-[:{edge['type']}]->(b)
                RETURN a, b
                """,
                source=source,
                target=target
            )
        
            if result.peek() is None:
                print("❌ RELATION FAILED:", edge)
        
        print("✅ Relationships created")
 

        # -------------------------

        # ENRICH DATA

        # -------------------------

        enrich_vm_metadata(session)

 

        print("🚀 Graph ready (dynamic Azure mode)")

 

 

# -----------------------------------------

# ENTRY

# -----------------------------------------

if __name__ == "__main__":

    load()

