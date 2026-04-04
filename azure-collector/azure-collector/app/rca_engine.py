from neo4j import GraphDatabase
from datetime import datetime, timezone
 
class RCAEngine:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
 
    def execute(self, query, params=None):
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [r.data() for r in result]
 
    # =====================================
    # MAIN RCA ENGINE (FULL DETAILED OUTPUT)
    # =====================================
    def analyze_path(self, vm, port):
 
        path = ["VM", "NIC"]
        issues = []
        root_cause = "System healthy"
        fix = "No action needed"
        confidence = 100
 
        # -----------------------------
        # 1. VM EXISTS
        # -----------------------------
        if not self.execute("MATCH (v:VM {name:$vm}) RETURN v", {"vm": vm}):
            return {
                "vm": vm,
                "path": [],
                "issues": ["❌ VM not found"],
                "root_cause": "VM does not exist",
                "fix": "Verify VM name",
                "confidence": 100
            }
 
        # -----------------------------
        # 2. LOAD BALANCER
        # -----------------------------
        lb = self.execute("""
        MATCH (vm:VM {name:$vm})-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (lb:LoadBalancer)-[:BALANCES]->(nic)
        RETURN lb.name AS lb
        """, {"vm": vm})
 
        lb_present = any(x.get("lb") for x in lb)
 
        if lb_present:
            path.insert(0, "LoadBalancer")
            issues.append(f"✔ Traffic via LB: {lb[0]['lb']}")
        else:
            issues.append("⚠ No Load Balancer")
 
        # LB MISCONFIG
        lb_check = self.execute("""
        MATCH (lb:LoadBalancer)
        OPTIONAL MATCH (lb)-[:BALANCES]->(nic)<-[:HAS_NIC]-(vm:VM {name:$vm})
        RETURN nic
        """, {"vm": vm})
 
        if lb_check and not any(x["nic"] for x in lb_check):
            issues.append("❌ VM not in LB backend pool")
 
        # -----------------------------
        # 3. PUBLIC IP
        # -----------------------------
        pip = self.execute("""
        MATCH (vm:VM {name:$vm})-[:HAS_NIC]->(nic)-[:HAS_PUBLIC_IP]->(pip)
        RETURN pip.name AS pip
        """, {"vm": vm})
 
        pip_present = len(pip) > 0
 
        if pip_present:
            path.insert(0, "PublicIP")
            issues.append(f"✔ Public IP: {pip[0]['pip']}")
        else:
            if lb_present:
                issues.append("⚠ No Public IP (LB present)")
            else:
                issues.append("❌ No Public IP attached")
 
        # -----------------------------
        # 4. NSG
        # -----------------------------
        path.append("NSG")
 
        rules = self.execute("""
        MATCH (vm:VM {name:$vm})-[:HAS_NIC]->()-[:SECURED_BY]->(nsg)-[:HAS_RULE]->(r)
        RETURN r.port AS port, r.access AS access, r.priority AS priority
        """, {"vm": vm})
 
        port_allowed = True
 
        if rules:
            rules = sorted(rules, key=lambda x: x["priority"])
 
            for r in rules:
                if str(r["port"]) in [str(port), "*"]:
                    if r["access"] == "deny":
                        port_allowed = False
                        issues.append(f"❌ NSG blocks port {port} (priority {r['priority']})")
                    else:
                        issues.append(f"✔ NSG allows port {port} (priority {r['priority']})")
                    break
        else:
            issues.append("✔ No NSG (open)")
 
        # -----------------------------
        # 5. ROUTE TABLE + BLACKHOLE
        # -----------------------------
        path.append("RouteTable")
 
        routes = self.execute("""
        MATCH (vm:VM {name:$vm})-[:HAS_NIC]->()-[:IN_SUBNET]->()
        -[:USES_ROUTE_TABLE]->(rt)-[:HAS_ROUTE]->(r)
        RETURN r.address_prefix AS prefix, r.next_hop AS hop
        """, {"vm": vm})
 
        blackhole = False
 
        if routes:
            issues.append("✔ Route Table attached")
 
            for r in routes:
                if r["prefix"] == "0.0.0.0/0" and r["hop"] == "None":
                    blackhole = True
                    issues.append("❌ Blackhole route blocking internet")
        else:
            issues.append("⚠ No Route Table (default routing)")
 
        # -----------------------------
        # 6. INTERNET CHECK
        # -----------------------------
        if not port_allowed:
            issues.append("❌ Traffic blocked by NSG")
 
        elif blackhole:
            issues.append("❌ Internet blocked by route table")
 
        elif lb_present:
            issues.append("✔ Internet reachable via Load Balancer")
 
        elif pip_present:
            issues.append("✔ Internet reachable via Public IP")
 
        else:
            issues.append("❌ No Internet entry point")
 
        # -----------------------------
        # 7. METRICS
        # -----------------------------
        path.append("Metrics")
 
        metrics = self.get_latest_metrics(vm)
 
        cpu = 0
        metrics_issue = False
 
        if not metrics:
            metrics_issue = True
            issues.append("⚠ No metrics available (agent issue)")
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
 
                    if diff > 60:
                        metrics_issue = True
                        issues.append("⚠ Metrics stale")
            except:
                metrics_issue = True
 
        # -----------------------------
        # 8. HEALTH
        # -----------------------------
        if metrics_issue:
            issues.append("⚠ VM state unknown (metrics missing)")
        else:
            issues.append("✔ VM running")
 
            if cpu > 80:
                issues.append("🔥 High CPU usage")
            else:
                issues.append("✔ CPU normal")
 
        # -----------------------------
        # 9. ROOT CAUSE PRIORITY
        # -----------------------------
        text = " ".join(issues)
 
        if "Blackhole route" in text:
            root_cause = "Blackhole route"
            fix = "Update route table next hop to Internet"
            confidence = 95
 
        elif "NSG blocks" in text:
            root_cause = "Traffic blocked by NSG"
            fix = "Allow port in NSG"
            confidence = 90
 
        elif "backend pool" in text:
            root_cause = "Load Balancer misconfiguration"
            fix = "Add VM to backend pool"
            confidence = 92
 
        elif "High CPU" in text:
            root_cause = "High CPU usage"
            fix = "Scale VM or reduce load"
            confidence = 90
 
        elif "metrics" in text.lower():
            root_cause = "Monitoring agent not sending data"
            fix = "Restart CIP agent"
            confidence = 80
 
        elif "No Internet entry point" in text:
            root_cause = "No Public IP or Load Balancer"
            fix = "Attach Public IP or configure LB"
            confidence = 85
 
        return {
            "vm": vm,
            "path": path,
            "issues": issues,
            "root_cause": root_cause,
            "fix": fix,
            "confidence": confidence
        }
 
    # -----------------------------
    # METRICS
    # -----------------------------
    def get_latest_metrics(self, vm):
 
        result = self.execute("""
        MATCH (m:Metrics {vm:$vm})
        RETURN m.cpu AS cpu,
               m.network_in AS network_in,
               m.network_out AS network_out,
               m.timestamp AS ts
        ORDER BY ts DESC LIMIT 1
        """, {"vm": vm})
 
        return result[0] if result else None
 
    def close(self):
        self.driver.close()