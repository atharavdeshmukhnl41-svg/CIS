def parse_route_table(rt):
    routes = []

    if rt.routes:
        for r in rt.routes:
            routes.append({
                "name": r.name,
                "address_prefix": r.address_prefix,
                "next_hop_type": r.next_hop_type
            })

    return {
        "id": rt.id,
        "name": rt.name,
        "routes": routes
    }