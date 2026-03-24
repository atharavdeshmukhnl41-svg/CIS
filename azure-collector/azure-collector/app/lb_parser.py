def parse_load_balancer(lb):
    data = {
        "id": lb.id,
        "name": lb.name,
        "frontend_ips": [],
        "backend_pools": [],
        "rules": []
    }

    # Frontend IPs
    if lb.frontend_ip_configurations:
        for f in lb.frontend_ip_configurations:
            data["frontend_ips"].append(f.id)

    # Backend Pools
    if lb.backend_address_pools:
        for b in lb.backend_address_pools:
            data["backend_pools"].append(b.id)

    # Rules
    if lb.load_balancing_rules:
        for rule in lb.load_balancing_rules:
            data["rules"].append({
                "name": rule.name,
                "frontend_port": rule.frontend_port,
                "backend_port": rule.backend_port
            })

    return data