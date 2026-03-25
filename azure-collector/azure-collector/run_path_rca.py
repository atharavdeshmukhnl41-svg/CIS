from app.rca_engine import RCAEngine
from app.ai_explainer import AIExplainer
 
 
def main():
 
    vm = input("Enter VM name: ")
    port = input("Enter port: ")
 
    engine = RCAEngine()
    ai = AIExplainer()
 
    result = engine.analyze_path(vm, port)
 
    print("\n===== END-TO-END RCA =====\n")
 
    print("VM:", result["vm"])
    print("Path:", " → ".join(result["path"]))
 
    print("\nIssues:")
    for issue in result["issues"]:
        print(issue)
 
    # AI Explanation
    explanation = ai.generate_explanation(result)
 
    print("\n🧠 AI ANALYSIS:")
    print("Root Cause:", explanation["summary"])
    print("Fix:", explanation["fix"])
 
    engine.close()
 
 
if __name__ == "__main__":
    main()