"""Telemetry Harvester for OmegA."""
import json
import time

class TelemetryHarvester:
    LOG_FILE = "/home/mega/OmegA-Architecture/output/teleodynamics_telemetry.jsonl"

    @staticmethod
    def ingest(trace):
        """Append trace signal to JSONL log."""
        with open(TelemetryHarvester.LOG_FILE, "a") as f:
            f.write(json.dumps(trace.to_json()) + "\n")

    @staticmethod
    def query_hotspots():
        """Identify high-shear signals from logs."""
        hotspots = []
        try:
            with open(TelemetryHarvester.LOG_FILE, "r") as f:
                for line in f:
                    data = json.loads(line)
                    if data.get("shear_index", 0) > 0.5:
                        hotspots.append(data)
        except FileNotFoundError:
            pass
        return hotspots
