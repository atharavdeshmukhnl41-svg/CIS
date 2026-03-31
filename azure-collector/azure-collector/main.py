from app.azure_fetcher import AzureFetcher
from app.topology_builder import TopologyBuilder
from app.graph_loader import GraphLoader
from app.azure_db_fetcher import AzureDBFetcher
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

 
def main():
 
    print("Fetching Azure resources...")
    fetcher = AzureFetcher()
 
    vms = fetcher.get_vms()
    nics = fetcher.get_nics()
    subnets = fetcher.get_subnets()
    vnets = fetcher.get_vnets()
    nsgs = fetcher.get_nsgs()
    public_ips = fetcher.get_public_ips()
    route_tables = fetcher.get_route_tables()
    load_balancers = fetcher.get_load_balancers()
    db_fetcher = AzureDBFetcher()
    databases = db_fetcher.get_databases()
    
    print("DEBUG DB COUNT:", len(databases))

    # DEBUG PRINT (ADD HERE)
    for nsg in nsgs:
        print("NSG:", nsg.name)
    
        if nsg.security_rules:
            for r in nsg.security_rules:
                print("RULE RAW:", r.__dict__)

    # optional
    try:
        nat_gateways = fetcher.get_nat_gateways()
    except:
        nat_gateways = None
 

 
    print("Building topology...")
    builder = TopologyBuilder()
 
    topology = builder.build(
        vms=vms,
        nics=nics,
        subnets=subnets,
        vnets=vnets,
        nsgs=nsgs,
        public_ips=public_ips,
        route_tables=route_tables,
        load_balancers=load_balancers,
        nat_gateways=nat_gateways,
        databases=databases
    )
 
    print("Loading into Neo4j...")
    loader = GraphLoader()
 
    loader.load(topology)
    loader.close()
 
 
if __name__ == "__main__":
    main()