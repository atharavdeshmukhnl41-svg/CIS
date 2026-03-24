
class MetricsAnalyzer:

    def analyze_cpu(self, cpu):
        if cpu is None:
            return "Unknown"

        if cpu > 80:
            return "High CPU Usage"

        elif cpu > 50:
            return "Moderate CPU Usage"

        else:
            return "Healthy"