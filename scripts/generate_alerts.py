# Streams simulated cloud infrastructure failures into the running FastAPI gateway.
# Generates realistic SRE anomalies (CPU, database, security, storage) as JSON payloads.
#
# Usage:
#   python scripts/generate_alerts.py                                  # random scenarios forever
#   python scripts/generate_alerts.py --scenario database_disk --count 1
#   python scripts/generate_alerts.py --interval 10 --count 10

import argparse
import random
import time
from datetime import datetime

import requests

DEFAULT_INGEST_URL = "http://127.0.0.1:8000/ingest"

# Highly realistic simulation payloads for the SRE demo
INCIDENTS = {
    "auth_latency": {
        "service_name": "Auth-Service",
        "severity": "WARNING",
        "message": "Latency spike detected on /login endpoint: 1540ms",
        "infrastructure_id": "pod-104.22.81.9"
    },
    "connection_pool": {
        "service_name": "Database-Cluster",
        "severity": "CRITICAL",
        "message": "Connection pool exhausted. Failed to allocate socket to client.",
        "infrastructure_id": "db-primary-rds-01"
    },
    "payment_info": {
        "service_name": "Payment-Gateway",
        "severity": "INFO",
        "message": "Webhook received from Stripe. Transaction TXN_88192 completed successfully.",
        "infrastructure_id": "gateway-node-abc"
    },
    "ddos": {
        "service_name": "Nginx-Ingress",
        "severity": "CRITICAL",
        "message": "DDOS alert: Request rate from IP 198.51.100.42 exceeded rate limits (5000 req/sec)",
        "infrastructure_id": "ingress-edge-02"
    },
    "storage_capacity": {
        "service_name": "Storage-Service",
        "severity": "WARNING",
        "message": "S3 bucket space reaching capacity limits. Current utilization at 89.4%.",
        "infrastructure_id": "bucket-assets-prod"
    },
    "database_disk": {
        "service_name": "postgresql-db-01",
        "severity": "CRITICAL",
        "message": "disk_utilization_percent > 95%",
        "infrastructure_id": "postgresql-db-01"
    },
}


def build_payload(scenario: str) -> dict:
    incident = INCIDENTS[scenario]
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "service_name": incident["service_name"],
        "severity": incident["severity"],
        "message": incident["message"],
        "infrastructure_id": incident["infrastructure_id"]
    }


def stream_logs(url: str, scenario: str | None, interval: float | None, count: int | None) -> None:
    print("🚀 Starting Sentinel-Ops Real-time Log Stream Generator...")
    print("Press Ctrl+C to stop streaming.\n")

    sent = 0
    while count is None or sent < count:
        payload = build_payload(scenario or random.choice(list(INCIDENTS)))

        try:
            # Send the simulated system log to our FastAPI gateway
            response = requests.post(url, json=payload, timeout=3)
            if response.status_code == 200:
                print(f"📡 Sent [{payload['severity']}] log from {payload['service_name']} -> Server Response: {response.json()['status']}")
            else:
                print(f"❌ Failed to stream log. Server returned status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"⚠️ Connection Error! Is the API server running at {url}?")

        sent += 1
        if count is not None and sent >= count:
            break

        # Pause before sending the next system anomaly
        time.sleep(interval if interval is not None else random.uniform(2.0, 4.0))


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream simulated infrastructure alerts into Sentinel-Ops.")
    parser.add_argument("--scenario", choices=sorted(INCIDENTS), help="Send only this scenario (default: random)")
    parser.add_argument("--interval", type=float, help="Seconds between alerts (default: random 2-4s)")
    parser.add_argument("--count", type=int, help="Number of alerts to send (default: unlimited)")
    parser.add_argument("--url", default=DEFAULT_INGEST_URL, help=f"Ingestion endpoint (default: {DEFAULT_INGEST_URL})")
    args = parser.parse_args()

    try:
        stream_logs(args.url, args.scenario, args.interval, args.count)
    except KeyboardInterrupt:
        print("\n👋 Generator stopped.")


if __name__ == "__main__":
    main()
