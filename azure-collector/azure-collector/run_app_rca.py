from app.rca_engine import RCAEngine
from app.dependency_mapper import DependencyMapper
 
 
def main():
 
    engine = RCAEngine()
    mapper = DependencyMapper()
 
    app_name = input("Enter application name: ")
    port = input("Enter port: ")
 
    apps = mapper.map_application(app_name)
 
    print("\n===== APPLICATION RCA =====\n")
 
    if not apps:
        print("❌ No application mapping found")
        return
 
    for app in apps:
 
        print(f"App: {app['app']}")
        print(f"LoadBalancer: {app['lb']}")
 
        if not app["vms"]:
            print("❌ No VM attached to LoadBalancer")
            print("\n----------------------------\n")
            continue
 
        for vm in app["vms"]:
 
            result = engine.analyze_path(vm, port)
 
            if not result:
                print("❌ RCA failed for VM:", vm)
                continue
 
            print("\nVM:", vm)
            print("Path:", result["path"])
 
            for issue in result["issues"]:
                print(issue)
 
            # DATABASE CHECK
            db_ok, db_msg = engine.check_database(vm)
 
            if not db_ok:
                print("❌", db_msg)
            else:
                print("✔", db_msg)
 
        print("\n----------------------------\n")
 
 
if __name__ == "__main__":
    main()