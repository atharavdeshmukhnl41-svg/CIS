from app.rca_engine import RCAEngine
from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
 
 
class AlertEngine:
 
    def __init__(self):
        self.rca = RCAEngine()
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
 
    # =========================
    # CHECK METRICS & TRIGGER RCA
    # =========================
    def evaluate_vm(self, vm_name):
 
        metrics = self.rca.get_metrics(vm_name)
 
        if not metrics or "error" in metrics:
            return None
 
        alerts = []
 
        # CPU threshold
        if metrics["cpu"] and metrics["cpu"] > 80:
            alerts.append("High CPU")
 
        # No network activity
        if metrics["network_in"] == 0 and metrics["network_out"] == 0:
            alerts.append("No Network Activity")
 
        if not alerts:
            return None
 
        # Run RCA automatically
        rca_result = self.rca.analyze_path(vm_name, 80)
 
        alert_data = {
            "vm": vm_name,
            "alerts": alerts,
            "rca": rca_result
        }
 
        # Store in Neo4j
        self.store_alert(alert_data)
 
        return alert_data
 
    # =========================
    # STORE ALERT
    # =========================
    def store_alert(self, alert):
 
        query = """
        MERGE (vm:VM {name:$vm})
        CREATE (a:Alert {
            issues:$issues,
            path:$path,
            timestamp: datetime()
        })
        MERGE (vm)-[:HAS_ALERT]->(a)
        """
 
        with self.driver.session() as session:
            session.run(
                query,
                vm=alert["vm"],
                issues=alert["rca"]["issues"],
                path=alert["rca"]["path"]
            )