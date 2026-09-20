import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .scraper import sync_schedule

logger = logging.getLogger(__name__)


def start(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        sync_schedule,
        trigger="interval",
        hours=6,
        id="sync_schedule",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — running initial sync")
    sync_schedule()
    return scheduler
