from app.azure_metrics import AzureMetricsCollector

def main():
    collector = AzureMetricsCollector()
    collector.collect_all_vms_metrics()
    collector.close()
    print("✅ Metrics collection and Neo4j update complete!")

if __name__ == "__main__":
    main()