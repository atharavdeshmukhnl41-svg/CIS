from app.rca_engine import RCAEngine

def main():
    engine = RCAEngine()

    vm_name = input("Enter VM name: ")
    port = input("Enter port: ")

    print("\nTracing full connectivity path...\n")

    path = engine.trace_path(vm_name)

    if not path:
        print("❌ No path found (VM misconfigured)")
        return

    print("✔ Path Found:")
    print("VM → NIC → Subnet → VNet")

    result = engine.detect_break_point(vm_name, port)

    print("\n===== ANALYSIS =====\n")

    # Debug: show what result dictionary contains
    print("DEBUG: Result dictionary:", result)

    break_point = result.get("break")  # Safely get the key

    if break_point == "NSG":
        print("🚨 BREAK POINT: NSG")
        print(result.get("reason", "No reason provided"))

    elif break_point == "Topology":
        print("🚨 BREAK POINT: Missing network link")

    else:
        print("✅ No issue found in current checks")

    engine.close()

if __name__ == "__main__":
    main()