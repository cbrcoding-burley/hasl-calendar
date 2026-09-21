import logging
import os

from sqlalchemy import text

from .models import engine, init_db, reset_db

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
        _add_columns()
    logger.info("Migration complete")


def _add_columns():
    """Add new columns to existing tables without losing data."""
    with engine.connect() as conn:
        existing = {
            row[1] for row in conn.execute(text("PRAGMA table_info(teams)")).fetchall()
        }
        if "hasl_id" not in existing:
            conn.execute(text("ALTER TABLE teams ADD COLUMN hasl_id VARCHAR"))
            conn.commit()
            logger.info("Added teams.hasl_id column")


if __name__ == "__main__":
    main()
