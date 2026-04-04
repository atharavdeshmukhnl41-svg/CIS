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
    # MAIN ALERT EVALUATION
    # =========================
    def evaluate_vm(self, vm_name, port=80):
 
        rca_result = self.rca.analyze_path(vm_name, port)
 
        if not rca_result:
            return {
                "vm": vm_name,
                "alerts": ["❌ RCA failed"]
            }
 
        issues = rca_result.get("issues", [])
        alerts = []
 
        # 🔥 CRITICAL FIX: derive alerts from RCA issues
        for issue in issues:
            if "❌" in issue or "🔥" in issue or "⚠" in issue:
                alerts.append(issue)
 
        # fallback
        if not alerts:
            alerts.append("✔ System healthy")
 
        alert_data = {
            "vm": vm_name,
            "alerts": alerts,
            "rca": rca_result
        }
 
        # store in Neo4j
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
            root_cause:$root,
            timestamp: datetime()
        })
        MERGE (vm)-[:HAS_ALERT]->(a)
        """
 
        with self.driver.session() as session:
            session.run(
                query,
                vm=alert["vm"],
                issues=alert["rca"].get("issues", []),
                path=alert["rca"].get("path", []),
                root=alert["rca"].get("root_cause", "")
            )