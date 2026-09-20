import logging
import os

from .scraper import sync_via_api

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

log = logging.getLogger(__name__)


def main():
    base_url = os.environ["HASL_CALENDAR_URL"]
    log.info("Starting sync against %s", base_url)
    sync_via_api(base_url)
    log.info("Sync complete")


if __name__ == "__main__":
    main()
