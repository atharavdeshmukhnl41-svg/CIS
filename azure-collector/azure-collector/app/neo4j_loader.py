from neo4j import GraphDatabase
from app.config import *


class Neo4jLoader:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

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

                # ✅ Add extra properties dynamically
                if "port" in node:
                    props["port"] = str(node["port"])

                if "access" in node:
                    props["access"] = node["access"]

                if "priority" in node:
                    props["priority"] = int(node["priority"])  # ✅ FIX

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
    
        self.execute(query, {
            "vm": vm,
            "cpu": cpu,
            "net_in": net_in,
            "net_out": net_out
        })

        print("Loaded into Neo4j!")