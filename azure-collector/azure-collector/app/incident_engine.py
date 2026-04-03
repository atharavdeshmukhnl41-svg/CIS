from app.rca_engine import RCAEngine
from app.priority_engine import PriorityEngine
from neo4j import GraphDatabase
from app.remediation_engine import RemediationEngine
 
 
class IncidentEngine:
 
    def __init__(self):
        self.rca = RCAEngine()
        self.priority = PriorityEngine()
        self.remediation = RemediationEngine()
 
        self.driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
 
    # -----------------------------------------
    # OPTIONAL (NOT USED ANYMORE)
    # -----------------------------------------
    def get_active_vms(self):
        query = """
        MATCH (m:Metrics)
        RETURN DISTINCT m.vm AS vm
        """
        with self.driver.session() as session:
            result = session.run(query).data()
 
        return [r["vm"] for r in result if r.get("vm")]
 
    # -----------------------------------------
    # MAIN INCIDENT ENGINE (FINAL FIXED)
    # -----------------------------------------
    def analyze_infrastructure(self, vms, port):
 
        incident_map = {}
 
        for vm in vms:
 
            try:
                result = self.rca.analyze_path(vm, port)
 
                if not result or not isinstance(result, dict):
                    print(f"❌ Invalid RCA result for {vm}")
                    continue
 
            except Exception as e:
                print(f"❌ RCA ERROR for {vm}:", e)
                continue
 
            root = str(result.get("root_cause") or "unknown").strip()
            fix = result.get("fix", "No fix available")
            confidence = result.get("confidence", 50)
 
            # 🔥 SKIP HEALTHY SYSTEMS
            if root.lower() == "system healthy":
                continue
 
            root_key = root.lower()
 
            if root_key not in incident_map:
                incident_map[root_key] = {
                    "root_cause": root,
                    "affected_vms": set(),
                    "fix": fix,
                    "confidence": confidence
                }
 
            incident_map[root_key]["affected_vms"].add(vm)
 
        # -----------------------------------------
        # BUILD FINAL INCIDENT LIST
        # -----------------------------------------
        incidents = []
 
        for i, data in enumerate(incident_map.values()):
 
            affected_vms = list(data["affected_vms"])
 
            # SAFE PRIORITY
            try:
                priority = self.priority.calculate_priority(
                    data["root_cause"],
                    affected_vms,
                    data["confidence"]
                )
            except Exception as e:
                print("⚠ Priority error:", e)
                priority = "MEDIUM"
 
            # SAFE REMEDIATION
            try:
                steps = self.remediation.get_steps(data["root_cause"])
            except Exception as e:
                print("⚠ Remediation error:", e)
                steps = ["No remediation steps available"]
 
            incidents.append({
                "incident_id": f"INC-{1000 + i}",
                "root_cause": data["root_cause"],
                "affected_vms": affected_vms,
                "fix": data["fix"],
                "steps": steps,
                "confidence": data["confidence"],
                "priority": priority
            })
 
        # -----------------------------------------
        # SORT BY PRIORITY
        # -----------------------------------------
        priority_order = {
            "CRITICAL": 1,
            "HIGH": 2,
            "MEDIUM": 3,
            "LOW": 4
        }
 
        incidents = sorted(
            incidents,
            key=lambda x: priority_order.get(x["priority"], 5)
        )
 
        return incidents