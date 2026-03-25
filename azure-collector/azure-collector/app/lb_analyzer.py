class LBAnalyzer:
 
    def __init__(self, driver):
        self.driver = driver
 
    def check_lb(self, vm_name, port):
 
        query = """
        MATCH (lb:LoadBalancer)
        OPTIONAL MATCH (lb)-[:HAS_BACKEND]->(nic)<-[:HAS_NIC]-(vm:VM {name:$vm})
        OPTIONAL MATCH (lb)-[:HAS_RULE]->(rule)
        RETURN lb.name AS lb,
               COUNT(nic) AS backend_count,
               COLLECT(rule) AS rules
        """
 
        with self.driver.session() as session:
            results = session.run(query, vm=vm_name)
 
            for r in results:
 
                lb_name = r["lb"]
                backend_count = r["backend_count"]
                rules = r["rules"]
 
                # CASE 1: LB exists but VM not attached
                if backend_count == 0:
                    return False, f"VM not attached to LoadBalancer: {lb_name}"
 
                # CASE 2: Check rule for port
                rule_match = False
 
                for rule in rules:
                    if rule:
                        if rule["frontend_port"] == port or rule["backend_port"] == port:
                            rule_match = True
                            break
 
                if not rule_match:
                    return False, f"No LoadBalancer rule for port {port}"
 
                # CASE 3: Everything OK
                return True, f"Traffic via LoadBalancer: {lb_name}"
 
            return True, "No LoadBalancer in path"