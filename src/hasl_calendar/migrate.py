import logging
import os

from .models import init_db, reset_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    if os.environ.get("RESET_DB_ON_START", "").lower() == "true":
        logger.warning("RESET_DB_ON_START is set — dropping and recreating all tables")
        reset_db()
    else:
        init_db()
    logger.info("Migration complete")


if __name__ == "__main__":
    main()
