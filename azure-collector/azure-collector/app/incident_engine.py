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
    # GET ONLY ACTIVE VMs (CRITICAL FIX)
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
    # MAIN INCIDENT ENGINE
    # -----------------------------------------
    def analyze_infrastructure(self, vms, port):
 
        active_vms = self.get_active_vms()
 
        # ❗ No active VMs
        if not active_vms:
            return []
 
        incident_map = {}
 
        for vm in vms:
 
            # ❌ Skip inactive VMs
            if vm not in active_vms:
                continue
 
            try:
                result = self.rca.analyze_path(vm, port)
            except Exception as e:
                print(f"RCA ERROR for {vm}:", e)
                continue
 
            root = result.get("root_cause", "unknown").strip()
            fix = result.get("fix", "No fix available")
            confidence = result.get("confidence", 50)
 
            # Normalize root cause key (avoid duplicates due to spacing/case)
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
 
            priority = self.priority.calculate_priority(
                data["root_cause"],
                affected_vms,
                data["confidence"]
            )
 
            steps = self.remediation.get_steps(data["root_cause"])
            
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
        # SORT BY PRIORITY (CRITICAL FIRST)
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