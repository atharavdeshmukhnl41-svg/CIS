from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
 
 
class GraphLoader:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
 
    def close(self):
        self.driver.close()
 
    def load(self, topology):
 
        with self.driver.session() as session:
 
            # CLEAN DB (IMPORTANT)
            session.run("MATCH (n) DETACH DELETE n")
 
            # =========================
            # CREATE NODES
            # =========================
            for node in topology["nodes"]:
            
                props = {k: v for k, v in node.items() if k not in ["id", "label"]}
            
                set_clause = ", ".join([f"n.{k} = ${k}" for k in props.keys()])
            
                session.run(
                    f"""
                    MERGE (n:{node['label']} {{id:$id}})
                    SET {set_clause}
                    """,
                    id=node["id"],
                    **props
                )
            # =========================
            # CREATE EDGES (FINAL FIX)
            # =========================
            for edge in topology["edges"]:
 
                session.run(
                    f"""
                    MATCH (a {{id:$source}})
                    MATCH (b {{id:$target}})
                    MERGE (a)-[:{edge['type']}]->(b)
                    """,
                    source=edge["source"],
                    target=edge["target"]
                )
 
        print("Loaded into Neo4j successfully!")