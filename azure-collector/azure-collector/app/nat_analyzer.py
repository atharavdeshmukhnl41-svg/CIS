from neo4j import GraphDatabase
 
 
class NATAnalyzer:
 
    def __init__(self, driver):
        self.driver = driver
 
    def check_nat(self, vm_name):
 
        with self.driver.session() as session:
 
            # Check Public IP first (direct outbound)
            public_ip_query = """
            MATCH (vm:VM {name:$vm})-[:HAS_NIC]->(nic)
            MATCH (nic)-[:HAS_PUBLIC_IP]->(pip)
            RETURN pip.name LIMIT 1
            """
 
            result = session.run(public_ip_query, vm=vm_name).single()
 
            if result:
                return True, "Outbound via Public IP"
 
            # Check NAT Gateway
            nat_query = """
            MATCH (vm:VM {name:$vm})-[:HAS_NIC]->(nic)
            MATCH (nic)-[:IN_SUBNET]->(subnet)
            MATCH (subnet)-[:HAS_NAT]->(nat)
            RETURN nat.name LIMIT 1
            """
 
            result = session.run(nat_query, vm=vm_name).single()
 
            if result:
                return True, "Outbound via NAT Gateway"
 
            return False, "No outbound path"