import os

from sqlalchemy import Column, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///hasl.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    slug = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    hasl_id = Column(String, nullable=True)

    home_games = relationship(
        "Game", foreign_keys="Game.home_team_slug", back_populates="home_team"
    )
    away_games = relationship(
        "Game", foreign_keys="Game.away_team_slug", back_populates="away_team"
    )

    def __repr__(self):
        return f"<Team slug={self.slug!r} name={self.name!r}>"


class Game(Base):
    __tablename__ = "games"

    # Stable ID: sha1 of (date|time|home_team_slug|away_team_slug), first 16 hex chars
    id = Column(String(16), primary_key=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    time = Column(String(5), nullable=False)  # HH:MM (24h)
    datetime_local = Column(String, nullable=False)  # ISO 8601 naive local
    timezone = Column(String, nullable=False, default="America/New_York")
    location = Column(String, nullable=False)
    league = Column(String, nullable=False)  # full league name e.g. "MEN'S REC LEAGUE"
    home_team_slug = Column(String, ForeignKey("teams.slug"), nullable=False)
    away_team_slug = Column(String, ForeignKey("teams.slug"), nullable=False)

    home_team = relationship(
        "Team", foreign_keys=[home_team_slug], back_populates="home_games"
    )
    away_team = relationship(
        "Team", foreign_keys=[away_team_slug], back_populates="away_games"
    )

    def __repr__(self):
        return f"<Game {self.date} {self.time} {self.league} home={self.home_team_slug!r} away={self.away_team_slug!r}>"


def init_db():
    Base.metadata.create_all(engine)


def reset_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
