"""
Local dev helper: runs sync_schedule in a background thread every 6 hours.

Not maintained — production uses the Railway cron service (hasl-scraper).
Run this alongside the Flask dev server if you want background syncing locally:

    uv run python dev/scheduler.py &
    uv run flask --app hasl_calendar.app run --debug
"""

import logging
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler

from hasl_calendar.scraper import sync_schedule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)

scheduler = BackgroundScheduler()
scheduler.add_job(sync_schedule, trigger="interval", hours=6, id="sync_schedule")
scheduler.start()
sync_schedule()

try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    scheduler.shutdown()
