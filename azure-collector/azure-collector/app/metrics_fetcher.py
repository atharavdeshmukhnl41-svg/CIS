from app.azure_metrics import AzureMetricsCollector
from app.azure_fetcher import AzureFetcher
 
 
class MetricsFetcher:
 
    def __init__(self):
        self.collector = AzureMetricsCollector()
        self.fetcher = AzureFetcher()
 
    # -----------------------------------------
    # SINGLE VM FETCH (USED BY OLD TEST CASES)
    # -----------------------------------------
    def fetch(self, vm_name):
 
        vms = self.fetcher.get_vms()
 
        if not vms:
            return self._empty_metrics()
 
        vm_data = None
 
        # ✅ Handle Azure VM objects safely
        for vm in vms:
            try:
                if vm.name == vm_name:
                    vm_data = vm
                    break
            except Exception:
                continue
 
        if not vm_data:
            print(f"❌ VM '{vm_name}' not found")
            return self._empty_metrics()
 
        # ✅ NEW: Pass full VM object (NOT resource_id)
        return self.collector.fetch_metrics(vm_data)
 
    # -----------------------------------------
    # ALL VMs FETCH (NEW - GENERIC)
    # -----------------------------------------
    def fetch_all(self):
 
        results = []
 
        vms = self.fetcher.get_vms()
 
        if not vms:
            return []
 
        for vm in vms:
            try:
                metrics = self.collector.fetch_metrics(vm)
 
                results.append({
                    "vm": vm.name,
                    "cpu": metrics.get("cpu", 0),
                    "network_in": metrics.get("network_in", 0),
                    "network_out": metrics.get("network_out", 0)
                })
 
            except Exception as e:
                print(f"❌ Error fetching metrics for {vm.name}: {e}")
 
        return results
 
    # -----------------------------------------
    # EMPTY METRICS (SAFE FALLBACK)
    # -----------------------------------------
    def _empty_metrics(self):
        return {
            "cpu": 0,
            "network_in": 0,
            "network_out": 0
        }