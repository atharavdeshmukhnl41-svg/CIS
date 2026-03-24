import json
from app.azure_fetcher import AzureFetcher
from app.topology_builder import TopologyBuilder


def main():
    print("Fetching Azure resources...")

    fetcher = AzureFetcher()

    vms = fetcher.get_vms()
    nics = fetcher.get_nics()
    vnets = fetcher.get_vnets()
    nsgs = fetcher.get_nsgs()
    public_ips = fetcher.get_public_ips()
    route_tables = fetcher.get_route_tables()   # ✅ NEW

    print("Building topology...")

    builder = TopologyBuilder()

    topology = builder.build(
        vms=vms,
        nics=nics,
        vnets=vnets,
        nsgs=nsgs,
        public_ips=public_ips,
        route_tables=route_tables   # ✅ FIX
    )

    print("Saving topology.json...")

    with open("topology.json", "w") as f:
        json.dump(topology, f, indent=2)

    print("\n✅ Topology generated successfully!")
    print(f"Nodes: {len(topology['nodes'])}")
    print(f"Edges: {len(topology['edges'])}")


if __name__ == "__main__":
    main()