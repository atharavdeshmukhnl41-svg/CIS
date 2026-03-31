from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
 
class GraphQueries:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
 
    def check_nsg_block(self, vm, port):
 
        query = """
        MATCH (vm:VM {name:$vm})-[:ATTACHED_TO]->(nic)-[:SECURED_BY]->(nsg)
        OPTIONAL MATCH (nsg)-[:HAS_RULE]->(rule)
        WHERE rule.port = $port AND rule.action = "DENY"
        RETURN rule
        """
 
        with self.driver.session() as session:
            result = session.run(query, {"vm": vm, "port": port}).data()
 
        return len(result) > 0
 
    def check_vm_exists(self, vm):
        query = "MATCH (v:VM {name:$vm}) RETURN v"
        with self.driver.session() as session:
            result = session.run(query, {"vm": vm}).data()
 
        return len(result) > 0
 
    def get_vm_path(self, vm):
        query = """
        MATCH (vm:VM {name:$vm})-[:ATTACHED_TO]->(nic)-[:SECURED_BY]->(nsg)
        RETURN vm.name AS vm, nic.name AS nic, nsg.name AS nsg
        """
 
        with self.driver.session() as session:
            result = session.run(query, {"vm": vm}).data()
 
        return result