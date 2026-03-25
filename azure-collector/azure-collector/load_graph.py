from neo4j import GraphDatabase
import json
import os
 
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
 
 
def load():
 
    with open("topology.json") as f:
        data = json.load(f)
 
    with driver.session() as session:
 
        session.run("MATCH (n) DETACH DELETE n")
 
        for node in data["nodes"]:
            label = node.pop("label")
            session.run(f"CREATE (n:{label} $props)", props=node)
 
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
 
 
if __name__ == "__main__":
    load()
