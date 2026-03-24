from app.route_rca import RouteRCA


def main():
    vm_name = input("Enter VM name: ")

    rca = RouteRCA()
    issues = rca.check_routes(vm_name)

    print("\n===== ROUTE TABLE RCA =====\n")

    if not issues:
        print("✅ No route issues detected")
    else:
        for i in issues:
            print(f"❌ {i}")

    rca.close()


if __name__ == "__main__":
    main()