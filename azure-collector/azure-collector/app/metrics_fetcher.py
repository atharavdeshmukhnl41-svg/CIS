from azure.identity import DefaultAzureCredential
from azure.monitor.query import MetricsQueryClient
from datetime import timedelta


class MetricsFetcher:
    def __init__(self):
        self.client = MetricsQueryClient(DefaultAzureCredential())

    def get_vm_cpu(self, vm_id):
        try:
            response = self.client.query_resource(
                resource_uri=vm_id,
                metric_names=["Percentage CPU"],
                timespan=timedelta(minutes=5)
            )

            if not response.metrics:
                return None

            metric = response.metrics[0]

            for ts in metric.timeseries:
                for point in ts.data:
                    if point.average is not None:
                        return point.average

            return None

        except Exception:
            return None