from neo4j import GraphDatabase

from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

 

 

class TopologyResolver:

 

    def __init__(self):

        self.driver = GraphDatabase.driver(

            NEO4J_URI,

            auth=(NEO4J_USER, NEO4J_PASSWORD)

        )

 

    # -----------------------------------------

    # RESOURCE GROUP

    # -----------------------------------------

    def get_vm_resource_group(self, vm):

 

        with self.driver.session() as session:

            result = session.run("""

                MATCH (v:VM {name:$vm})

                RETURN v.resource_group AS rg

            """, vm=vm).single()

 

            return result["rg"] if result else None

 

    # -----------------------------------------

    # NSG RESOLUTION (FIXED)

    # -----------------------------------------

    def get_nsg_for_vm(self, vm):

 

        with self.driver.session() as session:

            result = session.run("""

                MATCH (v:VM {name:$vm})

                -[:HAS_NIC]->

                (nic:NIC)

                -[:SECURED_BY]->

                (nsg:NSG)

                RETURN nsg.name AS nsg

                LIMIT 1

            """, vm=vm).single()

 

            return result["nsg"] if result else None

