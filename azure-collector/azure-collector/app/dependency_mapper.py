from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
 
 
class DependencyMapper:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
 
    def close(self):
        self.driver.close()
 
    def map_application(self, app_name):
    
        query = """
        MATCH (lb:LoadBalancer)
    
        OPTIONAL MATCH (lb)-[:HAS_BACKEND]->(nic)
        OPTIONAL MATCH (vm:VM)-[:HAS_NIC]->(nic)
    
        RETURN lb.name AS lb,
            collect(DISTINCT vm.name) AS vms
        """
    
        result_data = []
    
        with self.driver.session() as session:
            result = session.run(query)
    
            for r in result:
    
                result_data.append({
                    "app": app_name,
                    "lb": r["lb"],
                    "vms": [v for v in r["vms"] if v]  # may be empty
                })
    
        return result_data