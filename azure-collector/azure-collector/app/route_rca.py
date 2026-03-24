from neo4j import GraphDatabase
from app.config import *


class RouteRCA:

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def check_routes(self, vm_name):
        query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
        MATCH (nic)-[:IN_SUBNET]->(subnet)
        OPTIONAL MATCH (rt:RouteTable)-[:HAS_ROUTE]->(route)
        RETURN route
        """

        issues = []

        with self.driver.session() as session:
            result = session.run(query, vm_name=vm_name)

            for record in result:
                route = record["route"]

                if route and route["next_hop"] in ["None", "Blackhole"]:
                    issues.append(
                        f"Traffic blocked by route: {route['name']}"
                    )

        return issues

    def close(self):
        self.driver.close()