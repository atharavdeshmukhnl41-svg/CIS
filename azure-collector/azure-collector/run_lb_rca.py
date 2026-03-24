from app.lb_rca import LB_RCA


def main():
    vm_name = input("Enter VM name: ")
    port = input("Enter port: ")

    lb = LB_RCA()
    issues = lb.check_lb_path(vm_name, port)

    print("\n===== LOAD BALANCER RCA =====\n")

    if not issues:
        print("✅ Load Balancer configuration looks OK")
    else:
        for issue in issues:
            print(f"❌ {issue}")

    lb.close()


if __name__ == "__main__":
    main()