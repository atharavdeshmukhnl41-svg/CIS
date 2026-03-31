from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
 
 
class DatabaseMapper:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
 
    def close(self):
        self.driver.close()
 
    # =========================
    # GENERIC EXECUTE (READ)
    # =========================
    def execute(self, query, params=None):
        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        except Exception as e:
            print("❌ DB READ ERROR:", str(e))
            return []
 
    # =========================
    # WRITE QUERY (FIXED)
    # =========================
    def write(self, query, params=None):
        try:
            with self.driver.session() as session:
                session.run(query, params or {})
                print("✅ DB WRITE SUCCESS")
        except Exception as e:
            print("❌ DB WRITE ERROR:", str(e))
 
    # =========================
    # MAP VM → DATABASE
    # =========================
    def map_vm_to_db(self, vm_name):
 
        query = """
        MATCH (vm:VM {name:$vm})
        OPTIONAL MATCH (vm)-[:CONNECTS_TO]->(db)
        RETURN db.name AS db
        """
 
        dbs = []
 
        try:
            with self.driver.session() as session:
                result = session.run(query, vm=vm_name)
 
                for r in result:
                    if r["db"]:
                        dbs.append(r["db"])
 
        except Exception as e:
            print("❌ DB MAP ERROR:", str(e))
 
        return dbs