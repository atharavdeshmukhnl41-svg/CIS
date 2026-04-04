from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()
 
from app.azure_fetcher import AzureFetcher
 
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
 
def load():
 
    collector = AzureFetcher()
    data = collector.get_topology()
 
    if not data:
        print("❌ No topology data")
        return
 
    print("✅ Topology collected")
 
    with driver.session() as session:
 
        session.run("MATCH (n) DETACH DELETE n")
 
        # NODES
        for node in data["nodes"]:
 
            if "id" not in node:
                continue
 
            label = node.get("label", "Unknown")
            props = node.copy()
            props.pop("label", None)
 
            session.run(
                f"MERGE (n:{label} {{id:$id}}) SET n += $props",
                id=props["id"],
                props=props
            )
 
        print("✅ Nodes created")
 
        # RELATIONSHIPS
        for edge in data["edges"]:
 
            if not edge.get("source") or not edge.get("target"):
                continue
 
            session.run(
                f"""
                MATCH (a {{id:$source}})
                MATCH (b {{id:$target}})
                MERGE (a)-[:{edge['type']}]->(b)
                """,
                source=edge["source"],
                target=edge["target"]
            )
 
        print("✅ Relationships created")
        print("🚀 Graph ready")
 
if __name__ == "__main__":
    load()