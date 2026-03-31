from neo4j import GraphDatabase
from app.metrics_fetcher import MetricsFetcher
 
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "password"
 
 
def main():
    vm_name = input("Enter VM name: ")
 
    fetcher = MetricsFetcher()
    metrics = fetcher.fetch(vm_name)
 
    print("\n===== METRICS =====")
    print(metrics)
 
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
 
    with driver.session() as session:
        session.run("""
        CREATE (m:Metrics {
            vm: $vm,
            cpu: $cpu,
            network_in: $network_in,
            network_out: $network_out,
            timestamp: datetime()
        })
        """, {
            "vm": vm_name,
            "cpu": metrics["cpu"],
            "network_in": metrics["network_in"],
            "network_out": metrics["network_out"]
        })
 
    driver.close()
    print("✔ Metrics stored in Neo4j")
 
 
if __name__ == "__main__":
    main()