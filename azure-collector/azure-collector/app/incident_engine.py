from app.rca_engine import RCAEngine
from app.remediation_engine import RemediationEngine
from neo4j import GraphDatabase
 
class IncidentEngine:
 
    def __init__(self):
        self.rca = RCAEngine()
        self.remediation = RemediationEngine()
 
        self.driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
 
    # =========================
    # GET ACTIVE VMs
    # =========================
    def get_active_vms(self):
 
        with self.driver.session() as session:
            data = session.run("""
            MATCH (v:VM)
            RETURN DISTINCT v.name AS vm
            """).data()
 
        return [r["vm"] for r in data if r.get("vm")]
 
    # =========================
    # INCIDENT ENGINE
    # =========================
    def analyze_infrastructure(self, vms, port):
 
        vm_list = self.get_active_vms()
 
        if not vm_list:
            return []
 
        incident_map = {}
 
        for vm in vm_list:
 
            try:
                result = self.rca.analyze_path(vm, port)
            except Exception as e:
                print(f"RCA ERROR {vm}:", e)
                continue
 
            root = result.get("root_cause", "unknown")
            confidence = result.get("confidence", 80)
 
            # =========================
            # 🔥 ROOT CAUSE MAPPING
            # =========================
            if root == "Blackhole route":
                fix = "Update route table next hop to Internet"
                priority = "CRITICAL"
                confidence = 95
 
            elif root == "NSG blocking":
                fix = "Allow required port in NSG"
                priority = "HIGH"
 
            elif root == "LB misconfiguration":
                fix = "Attach VM NIC to Load Balancer backend pool"
                priority = "HIGH"
 
            elif root == "Agent not running":
                fix = "Restart CIP agent service"
                priority = "HIGH"
 
            elif root == "High CPU":
                fix = "Scale VM or reduce workload"
                priority = "MEDIUM"
 
            elif root == "No Internet":
                fix = "Attach Public IP or Load Balancer"
                priority = "HIGH"
 
            else:
                fix = "No action needed"
                priority = "LOW"
 
            key = root.lower()
 
            if key not in incident_map:
                incident_map[key] = {
                    "root_cause": root,
                    "affected_vms": set(),
                    "fix": fix,
                    "priority": priority,
                    "confidence": confidence
                }
 
            incident_map[key]["affected_vms"].add(vm)
 
        # =========================
        # BUILD INCIDENT LIST
        # =========================
        incidents = []
 
        for i, data in enumerate(incident_map.values()):
 
            incidents.append({
                "incident_id": f"INC-{1000 + i}",
                "root_cause": data["root_cause"],
                "affected_vms": list(data["affected_vms"]),
                "fix": data["fix"],
                "steps": self.remediation.get_steps(data["root_cause"]),
                "confidence": data["confidence"],
                "priority": data["priority"]
            })
 
        # =========================
        # SORT BY PRIORITY
        # =========================
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