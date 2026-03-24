from app.internet_rca import InternetRCA
from app.unified_rca import UnifiedRCA


def main():
    vm_name = input("Enter VM name: ")
    port = input("Enter port: ")

    internet = InternetRCA()
    unified = UnifiedRCA()

    result = unified.analyze(vm_name, port)
    internet_result = internet.check_public_access(vm_name)

    print("\n===== INTERNET RCA =====\n")
    print(f"VM: {vm_name}\n")

    # Internet check
    print(f"Internet Access: {internet_result['status']}")

    # Existing RCA
    if result["issues"]:
        print("\nIssues:")
        for issue in result["issues"]:
            print(f"❌ {issue}")

    print("\n🚨 FINAL ROOT CAUSE:")
    if internet_result["status"] == "No Public IP":
        print("→ No Public IP attached")
    elif result["issues"]:
        print(f"→ {result['issues'][0]}")
    else:
        print("→ No major issue detected")

    internet.close()
    unified.close()


if __name__ == "__main__":
    main()