from app.rca_engine import RCAEngine


def main():
    vm_name = input("Enter VM name: ")

    engine = RCAEngine()

    result = engine.analyze_vm_health(vm_name)

    print("\n===== VM HEALTH =====\n")

    print("VM:", result.get("vm"))
    print("CPU:", result.get("cpu"))
    print("Status:", result.get("status"))

    if result.get("root_cause"):
        print("\n🚨 Root Cause:")
        print("→", result.get("root_cause"))

    if result.get("fix"):
        print("\n🔧 Fix:")
        print("→", result.get("fix"))

    if result.get("error"):
        print("\n❌ Error:")
        print(result.get("error"))

    engine.close()


if __name__ == "__main__":
    main()