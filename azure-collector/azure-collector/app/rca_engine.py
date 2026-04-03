from neo4j import GraphDatabase
from datetime import datetime, timezone
 
class RCAEngine:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
 
    # -----------------------------------------
    # HELPER
    # -----------------------------------------
    def execute(self, query, params=None):
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]
 
    # -----------------------------------------
    # MAIN RCA
    # -----------------------------------------
    def analyze_path(self, vm, port):
 
        path = ["VM"]
        issues = []
 
        # -----------------------------
        # 1. VM CHECK
        # -----------------------------
        vm_check = self.execute(
            "MATCH (v:VM {name:$vm}) RETURN v",
            {"vm": vm}
        )
 
        if not vm_check:
            return {
                "vm": vm,
                "path": [],
                "issues": ["❌ VM not found"],
                "root_cause": "VM does not exist",
                "fix": "Verify VM name",
                "confidence": 100
            }
 
        # -----------------------------
        # 2. NIC
        # -----------------------------
        path.append("NIC")
 
        # -----------------------------
        # 3. LOAD BALANCER
        # -----------------------------
        lb = self.execute("""
        MATCH (vm:VM {name:$vm})-[:HAS_NIC]->(nic)<-[:BALANCES]-(lb:LoadBalancer)
        RETURN lb.name AS lb
        """, {"vm": vm})
 
        if lb:
            path.insert(0, "LoadBalancer")
            issues.append(f"✔ Traffic via LB: {lb[0]['lb']}")
        else:
            issues.append("⚠ No Load Balancer")
 
        # -----------------------------
        # 4. PUBLIC IP
        # -----------------------------
        pip = self.execute("""
        MATCH (vm:VM {name:$vm})-[:HAS_NIC]->(nic)-[:HAS_PUBLIC_IP]->(pip)
        RETURN pip.name AS pip
        """, {"vm": vm})
 
        if pip:
            path.insert(0, "PublicIP")
            issues.append(f"✔ Public IP attached: {pip[0]['pip']}")
        else:
            issues.append("❌ No Public IP attached")
 
        # -----------------------------
        # 5. NSG
        # -----------------------------
        path.append("NSG")
 
        rules = self.execute("""
        MATCH (vm:VM {name:$vm})-[:HAS_NIC]->()-[:SECURED_BY]->(nsg)-[:HAS_RULE]->(r)
        RETURN r.port AS port, r.access AS access, r.priority AS priority
        """, {"vm": vm})
 
        port_allowed = True
 
        if rules:
            rules = sorted(rules, key=lambda x: x.get("priority", 9999))
            for r in rules:
                if str(r["port"]) in [str(port), "*"]:
                    if r["access"] == "deny":
                        port_allowed = False
                        issues.append(f"❌ NSG blocks port {port} (priority {r['priority']})")
                        break
                    else:
                        issues.append(f"✔ NSG allows port {port} (priority {r['priority']})")
                        break
        else:
            issues.append("✔ No NSG (open)")
 
        # -----------------------------
        # 6. ROUTE TABLE (SAFE FIX)
        # -----------------------------
        path.append("RouteTable")
 
        rt = self.execute("""
        MATCH (rt:RouteTable)
        RETURN rt.name AS rt LIMIT 1
        """)
 
        if rt:
            issues.append(f"✔ Route Table present: {rt[0]['rt']}")
        else:
            issues.append("⚠ No Route Table (default routing)")
 
        # -----------------------------
        # 7. INTERNET CHECK (FIXED)
        # -----------------------------
        if not port_allowed:
            issues.append("❌ Traffic blocked before VM")
 
        elif not pip and not lb:
            issues.append("❌ No Internet entry point")
 
        else:
            issues.append("✔ Internet reachable")
 
        # -----------------------------
        # 8. METRICS
        # -----------------------------
        path.append("Metrics")
 
        metrics = self.get_latest_metrics(vm)
 
        is_vm_down = False
        cpu = 0
 
        if not metrics:
            is_vm_down = True
            issues.append("❌ No metrics available")
 
        else:
            cpu = float(metrics.get("cpu") or 0)
            ts = metrics.get("ts")
 
            try:
                if ts:
                    if hasattr(ts, "to_native"):
                        ts = ts.to_native()
 
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
 
                    diff = (datetime.now(timezone.utc) - ts).total_seconds()
 
                    if diff > 30:
                        is_vm_down = True
            except:
                is_vm_down = True
 
        # -----------------------------
        # 9. HEALTH
        # -----------------------------
        if is_vm_down:
            issues.append("❌ VM DOWN")
        else:
            issues.append("✔ VM running")
 
        if cpu > 80:
            issues.append("🔥 High CPU")
        else:
            issues.append("✔ CPU normal")
 
        # -----------------------------
        # 10. FINAL ROOT CAUSE (FIXED PRIORITY)
        # -----------------------------
        text = " ".join(issues)
 
        # 🔴 1. VM DOWN
        if "VM DOWN" in text:
            return {
                "vm": vm,
                "path": path,
                "issues": issues,
                "root_cause": "VM is DOWN",
                "fix": "Start VM or restart monitoring agent",
                "confidence": 95
            }
 
        # 🔴 2. NSG BLOCK
        if "NSG blocks" in text:
            return {
                "vm": vm,
                "path": path,
                "issues": issues,
                "root_cause": "Traffic blocked by NSG",
                "fix": "Update NSG rule",
                "confidence": 90
            }
 
        # 🔴 3. HIGH CPU (🔥 FIX)
        if "High CPU" in text:
            return {
                "vm": vm,
                "path": path,
                "issues": issues,
                "root_cause": "High CPU usage on VM",
                "fix": "Scale VM or reduce workload",
                "confidence": 92
            }
 
        # 🔴 4. NETWORK ISSUE
        if "No Public IP" in text or "No Internet entry point" in text:
            return {
                "vm": vm,
                "path": path,
                "issues": issues,
                "root_cause": "No Public IP or Load Balancer",
                "fix": "Attach Public IP or Load Balancer",
                "confidence": 85
            }
 
        # 🟢 DEFAULT
        return {
            "vm": vm,
            "path": path,
            "issues": issues,
            "root_cause": "System healthy",
            "fix": "No action needed",
            "confidence": 100
        }
 
    # -----------------------------------------
    # METRICS
    # -----------------------------------------
    def get_latest_metrics(self, vm):
 
        query = """
        MATCH (m:Metrics {vm: $vm})
        RETURN m.cpu AS cpu,
               m.network_in AS network_in,
               m.network_out AS network_out,
               m.timestamp AS ts
        ORDER BY ts DESC
        LIMIT 1
        """
 
        result = self.execute(query, {"vm": vm})
 
        return result[0] if result else None
 
    def close(self):
        self.driver.close()