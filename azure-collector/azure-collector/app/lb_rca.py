from neo4j import GraphDatabase
from app.config import *


class LB_RCA:

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def check_lb_path(self, vm_name, port):
        query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (pool)<-[:HAS_BACKEND]-(lb:LoadBalancer)
        OPTIONAL MATCH (lb)-[:HAS_RULE]->(rule)
        RETURN lb, pool, rule
        """

        with self.driver.session() as session:
            result = session.run(query, vm_name=vm_name)

            issues = []

            for record in result:
                if record["lb"] is None:
                    issues.append("No Load Balancer configured")
                elif record["rule"] is None:
                    issues.append("No LB rule for port")

            return issues

    def close(self):
        self.driver.close()