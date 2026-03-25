from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
 
 
class RCAEngine:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
 
    def close(self):
        self.driver.close()
 
    # =========================
    # GET METRICS
    # =========================
    def get_metrics(self, vm_name):
 
        query = """
        MATCH (vm:VM {name:$vm})-[:HAS_METRIC]->(m)
        RETURN m.cpu AS cpu,
               m.network_in AS net_in,
               m.network_out AS net_out
        """
 
        with self.driver.session() as session:
            result = session.run(query, vm=vm_name)
            record = result.single()
 
            if not record:
                return None
 
            return {
                "cpu": record["cpu"],
                "network_in": record["net_in"],
                "network_out": record["net_out"]
            }
 
    # =========================
    # NSG ASSOCIATION
    # =========================
    def get_nsg_association(self, vm_name):
 
        query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
 
        OPTIONAL MATCH (nic)-[:SECURED_BY]->(nic_nsg:NSG)
 
        OPTIONAL MATCH (nic)-[:IN_SUBNET]->(subnet)
        OPTIONAL MATCH (subnet)-[:SECURED_BY]->(subnet_nsg:NSG)
 
        RETURN
        collect(DISTINCT nic_nsg.name) AS nic_nsgs,
        collect(DISTINCT subnet_nsg.name) AS subnet_nsgs
        """
 
        with self.driver.session() as session:
            result = session.run(query, vm_name=vm_name)
            record = result.single()
 
            if not record:
                return [], []
 
            return record["nic_nsgs"], record["subnet_nsgs"]
 
    # =========================
    # NSG RULES
    # =========================
    def get_nsg_rules(self, vm_name):
 
        query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
 
        OPTIONAL MATCH (nic)-[:SECURED_BY]->(nsg)
        OPTIONAL MATCH (nsg)-[:HAS_RULE]->(rule)
 
        RETURN rule.name AS name,
               rule.port AS port,
               rule.access AS access,
               rule.priority AS priority
        """
 
        rules = []
 
        with self.driver.session() as session:
            result = session.run(query, vm_name=vm_name)
 
            for r in result:
                if r["name"] is None:
                    continue
 
                rules.append({
                    "name": r["name"],
                    "port": str(r["port"]),
                    "access": r["access"],
                    "priority": r["priority"] if r["priority"] else 65000
                })
 
        return rules
 
    # =========================
    # NSG EVALUATION
    # =========================
    def evaluate_nsg(self, rules, port):
 
        port = str(port)
 
        if not rules:
            return True, "No NSG rules found"
 
        rules = sorted(rules, key=lambda x: x["priority"])
 
        for rule in rules:
            if rule["port"] == port or rule["port"] == "*":
 
                if rule["access"] == "Deny":
                    return False, f"Blocked by NSG rule: {rule['name']}"
 
                if rule["access"] == "Allow":
                    return True, f"Allowed by NSG rule: {rule['name']}"
 
        return False, "Default Deny (no matching rule)"
 
    # =========================
    # DATABASE CHECK (FIXED POSITION)
    # =========================
    def check_database(self, vm_name):
 
        query = """
        MATCH (vm:VM {name:$vm})
        OPTIONAL MATCH (vm)-[:CONNECTS_TO]->(db:Database)
        RETURN collect(db.name) AS dbs
        """
 
        with self.driver.session() as session:
            result = session.run(query, vm=vm_name)
            record = result.single()
 
            if not record:
                return False, "No database connected"
 
            dbs = [d for d in record["dbs"] if d]
 
            if not dbs:
                return False, "No database connected"
 
            return True, f"Connected to DB: {', '.join(dbs)}"
 
    # =========================
    # MAIN RCA
    # =========================
    def analyze_path(self, vm_name, port):
 
        path = ["VM"]
        issues = []
 
        # NSG CHECK
        nic_nsgs, subnet_nsgs = self.get_nsg_association(vm_name)
 
        if len(nic_nsgs) == 0 and len(subnet_nsgs) == 0:
            issues.append("❌ No NSG associated (traffic open)")
        else:
            path.append("NSG")
 
        rules = self.get_nsg_rules(vm_name)
        allowed, message = self.evaluate_nsg(rules, port)
 
        if not allowed:
            issues.append(f"❌ {message}")
 
        # LOAD BALANCER CHECK
        lb_query = """
        MATCH (vm:VM {name:$vm})-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (lb:LoadBalancer)-[:HAS_BACKEND]->(nic)
        OPTIONAL MATCH (lb)-[:HAS_RULE]->(rule)
        RETURN lb.name AS lb, rule.port AS port
        """
 
        with self.driver.session() as session:
            result = session.run(lb_query, vm=vm_name)
 
            lb_found = False
            rule_found = False
 
            for r in result:
                if r["lb"]:
                    lb_found = True
 
                if r["port"] == str(port):
                    rule_found = True
 
            if lb_found:
                path.append("LoadBalancer")
 
            if lb_found and not rule_found:
                issues.append(f"❌ No Load Balancer rule for port {port}")
 
        # ROUTE CHECK
        route_query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
        MATCH (nic)-[:IN_SUBNET]->(subnet)
        OPTIONAL MATCH (rt:RouteTable)-[:ASSOCIATED_WITH]->(subnet)
        OPTIONAL MATCH (rt)-[:HAS_ROUTE]->(route)
        RETURN route.next_hop AS hop
        """
 
        with self.driver.session() as session:
            result = session.run(route_query, vm_name=vm_name)
 
            for r in result:
                if r["hop"] == "None":
                    issues.append("❌ Blackhole route detected")
                    path.append("RouteTable")
                    break
 
        # METRICS CHECK
        metrics = self.get_metrics(vm_name)
 
        if metrics:
            if metrics["cpu"] and metrics["cpu"] > 80:
                issues.append(f"❌ High CPU usage: {metrics['cpu']}%")
                path.append("Metrics")
 
            if metrics["network_in"] == 0 and metrics["network_out"] == 0:
                issues.append("❌ No network activity detected")
                path.append("Metrics")
 
        # FINAL RETURN (CRITICAL FIX)
        return {
            "vm": vm_name,
            "path": path,
            "issues": issues if issues else ["No issues detected"]
        }