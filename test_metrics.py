from src.observability.metrics import metrics_tracker

summary = metrics_tracker.get_summary()
print("Metrics tracker works!")
print("Summary:", summary)
