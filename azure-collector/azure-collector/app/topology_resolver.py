from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
 
 
class TopologyResolver:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
 
    # -----------------------------------------
    # GET RESOURCE GROUP
    # -----------------------------------------
    def get_vm_resource_group(self, vm):
 
        if not vm:
            print("❌ VM name is empty")
            return None
 
        with self.driver.session() as session:
            result = session.run("""
            MATCH (v:VM)
            WHERE v.name = $vm
            RETURN v.resource_group AS rg
            """, {"vm": vm}).data()
 
        if not result:
            print("❌ VM not found:", vm)
            return None
 
        rg = result[0].get("rg")
 
        if not rg:
            print("❌ RG missing for VM:", vm)
            return None
 
        print("✅ RG FOUND:", rg)
        return rg
 
    # -----------------------------------------
    # GET NSG
    # -----------------------------------------
    def get_nsg_for_vm(self, vm):
 
        if not vm:
            return None
 
        with self.driver.session() as session:
            result = session.run("""
            MATCH (v:VM {name:$vm})-[:HAS_NIC]->()-[:SECURED_BY]->(nsg)
            RETURN nsg.name AS nsg
            LIMIT 1
            """, {"vm": vm}).data()
 
        if not result:
            print("❌ NSG not found for VM:", vm)
            return None
 
        return result[0].get("nsg")