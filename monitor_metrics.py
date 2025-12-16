#!/usr/bin/env python3
"""Простой монитор ресурсов: CPU, память, сеть, диск."""
import psutil
import time
import csv
import sys
from datetime import datetime

INTERVAL = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
OUTPUT_FILE = sys.argv[2] if len(sys.argv) > 2 else "metrics_log.csv"

# Заголовок CSV
header = [
    "timestamp",
    "cpu_percent",
    "mem_percent",
    "bytes_sent_per_s",
    "bytes_recv_per_s",
    "disk_read_per_s",
    "disk_write_per_s"
]

prev_net = psutil.net_io_counters()
prev_disk = psutil.disk_io_counters()
prev_time = time.time()

with open(OUTPUT_FILE, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(header)

    try:
        while True:
            time.sleep(INTERVAL)
            now = time.time()
            delta = now - prev_time

            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent

            net = psutil.net_io_counters()
            disk = psutil.disk_io_counters()

            bytes_sent_per_s = (net.bytes_sent - prev_net.bytes_sent) / delta
            bytes_recv_per_s = (net.bytes_recv - prev_net.bytes_recv) / delta
            disk_read_per_s = (disk.read_bytes - prev_disk.read_bytes) / delta
            disk_write_per_s = (disk.write_bytes - prev_disk.write_bytes) / delta

            prev_net = net
            prev_disk = disk
            prev_time = now

            row = [
                datetime.utcnow().isoformat() + "Z",
                f"{cpu:.2f}",
                f"{mem:.2f}",
                f"{bytes_sent_per_s:.2f}",
                f"{bytes_recv_per_s:.2f}",
                f"{disk_read_per_s:.2f}",
                f"{disk_write_per_s:.2f}"
            ]
            writer.writerow(row)
            csvfile.flush()
            print(f"[METRICS] CPU: {cpu:5.1f}% | MEM: {mem:5.1f}% | NET: ↑{bytes_sent_per_s/1024:.1f} KB/s ↓{bytes_recv_per_s/1024:.1f} KB/s", flush=True)
    except KeyboardInterrupt:
        print("Мониторинг остановлен")
