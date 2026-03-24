from app.rca_engine import RCAEngine
from app.ai_explainer import AIExplainer


def main():
    vm_name = input("Enter VM name: ")
    port = input("Enter port: ")

    engine = RCAEngine()
    ai = AIExplainer()

    result = engine.analyze_path(vm_name, port)

    print("\n===== END-TO-END RCA =====\n")

    if "error" in result:
        print(result["error"])
        return

    print("VM:", result["vm"])
    print("Path:", " → ".join(result["path"]))

    print("\n🚨 Issues:")
    for issue in result["issues"]:
        if issue != "No issues detected":
            print("❌", issue)

    explanation = ai.generate_explanation(result)

    print("\n🧠 AI ANALYSIS:")
    print("Root Cause:", explanation["summary"])
    print("Fix:", explanation["fix"])


if __name__ == "__main__":
    main()