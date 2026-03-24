def parse_nsg_rules(nsg):
    rules = []

    for rule in nsg.security_rules:
        rules.append({
            "name": rule.name,
            "port": rule.destination_port_range if rule.destination_port_range else "*",
            "access": rule.access,
            "priority": rule.priority   # ✅ MUST be this
        })

    return rules