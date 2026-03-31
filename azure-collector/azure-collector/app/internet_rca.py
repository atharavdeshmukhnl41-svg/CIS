from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class InternetRCA:

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def check_public_access(self, vm_name):
        query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (pip:PublicIP)-[:SECURED_BY]->(nic)
        RETURN pip
        """

        with self.driver.session() as session:
            result = session.run(query, vm_name=vm_name)
            record = result.single()

            if not record or record["pip"] is None:
                return {
                    "status": "No Public IP",
                    "details": "VM is not exposed to internet"
                }

        return {
            "status": "Public IP Present",
            "details": "VM reachable from internet (subject to NSG)"
        }

    def close(self):
        self.driver.close()