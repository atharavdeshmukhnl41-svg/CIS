from app.rca_engine import RCAEngine

def main():
    engine = RCAEngine()

    vm_name = input("Enter VM name: ")
    port = input("Enter port (22/80/443): ")

    result = engine.check_port_reachability(vm_name, port)

    print("\n===== RESULT =====\n")

    if result["status"] == "Allow":
        print(f"✅ Port {port} is ALLOWED")
        print("Matched Rule:", result["rule"])

    elif result["status"] == "Deny":
        print(f"🚨 Port {port} is BLOCKED")
        print("Matched Rule:", result["rule"])

    else:
        print("⚠️ Unable to determine:", result["message"])

    engine.close()

if __name__ == "__main__":
    main()