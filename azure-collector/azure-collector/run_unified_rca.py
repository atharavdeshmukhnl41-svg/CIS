from app.unified_rca import UnifiedRCA


def main():
    rca = UnifiedRCA()

    vm_name = input("Enter VM name: ")
    port = input("Enter port: ")

    result = rca.analyze(vm_name, port)

    print("\n===== ROOT CAUSE ANALYSIS =====\n")
    print(f"VM: {result['vm']}\n")

    if not result["issues"]:
        print("✅ No issues detected")
    else:
        for i, issue in enumerate(result["issues"], 1):
            print(f"{i}. ❌ {issue}")

        print("\n🚨 FINAL ROOT CAUSE:")
        print(f"→ {result['issues'][0]}")

    rca.close()


if __name__ == "__main__":
    main()