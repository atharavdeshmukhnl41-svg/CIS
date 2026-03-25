class AppTopologyBuilder:
 
    def __init__(self):
        self.apps = []
 
    def map_application(self, app_name, vm_names, lb_name=None):
 
        return {
            "app": app_name,
            "vms": vm_names,
            "load_balancer": lb_name
        }