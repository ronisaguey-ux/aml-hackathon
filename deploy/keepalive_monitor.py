#!/usr/bin/env python3
"""
24/7 Keep-Alive & Health Monitor for AxiomMem.
Monitors endpoint health continuously, logs uptime and latency every 60 seconds,
and alerts on failures during the AML evaluation window.
"""

import sys
import time
import argparse
import logging
from pathlib import Path
import httpx

def run_monitor(base_url: str, interval_sec: int, log_path: str):
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info(f"Starting AxiomMem Keep-Alive Monitor -> {base_url} (interval: {interval_sec}s)")
    client = httpx.Client(timeout=10.0)

    consecutive_failures = 0
    while True:
        t0 = time.time()
        try:
            resp = client.get(f"{base_url.rstrip('/')}/health")
            latency_ms = (time.time() - t0) * 1000
            if resp.status_code == 200:
                consecutive_failures = 0
                data = resp.json()
                uptime = data.get("uptime_seconds", 0)
                logging.info(f"HEALTH_OK: latency={latency_ms:.1f}ms uptime={uptime}s provider={data.get('embedding_provider')}")
            else:
                consecutive_failures += 1
                logging.warning(f"HEALTH_DEGRADED: status={resp.status_code} text={resp.text[:100]} failures={consecutive_failures}")
        except Exception as e:
            consecutive_failures += 1
            logging.error(f"HEALTH_UNREACHABLE: error={str(e)} consecutive_failures={consecutive_failures}")

        time.sleep(interval_sec)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--log-file", default="data/keepalive.log")
    args = parser.parse_args()

    run_monitor(args.base_url, args.interval, args.log_file)
