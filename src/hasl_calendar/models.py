import os

from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///hasl.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)  # numeric ID from aplsteam{id}.htm
    name = Column(String, nullable=False)
    league = Column(String, nullable=True)  # S1-S4; populated later

    home_games = relationship(
        "Game", foreign_keys="Game.home_team_id", back_populates="home_team"
    )
    away_games = relationship(
        "Game", foreign_keys="Game.away_team_id", back_populates="away_team"
    )

    def __repr__(self):
        return f"<Team id={self.id} name={self.name!r}>"


class Game(Base):
    __tablename__ = "games"

    # Stable ID: sha1 of (date|time|location|home_team_id|away_team_id), first 16 hex chars
    id = Column(String(16), primary_key=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    time = Column(String(5), nullable=False)  # HH:MM (24h)
    datetime_local = Column(String, nullable=False)  # ISO 8601 naive local
    timezone = Column(String, nullable=False, default="America/New_York")
    location = Column(String, nullable=False)
    league = Column(String(2), nullable=False)  # S1-S4
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    home_team = relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_games"
    )
    away_team = relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_games"
    )

    def __repr__(self):
        return f"<Game {self.date} {self.time} {self.league} home={self.home_team_id} away={self.away_team_id}>"


def init_db():
    Base.metadata.create_all(engine)
