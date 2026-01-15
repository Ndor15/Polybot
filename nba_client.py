"""
NBA API Client - Real-time game data collection
"""
import requests
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from config import config

logger = logging.getLogger(__name__)


class NBAGame:
    """Represents a live NBA game with scoring data"""

    def __init__(self, game_id: str, home_team: str, away_team: str):
        self.game_id = game_id
        self.home_team = home_team
        self.away_team = away_team
        self.home_score = 0
        self.away_score = 0
        self.period = 0
        self.time_remaining = ""
        self.status = "scheduled"
        self.last_update = None

        # Momentum tracking
        self.score_history: List[Tuple[int, int, float]] = []  # (home, away, timestamp)
        self.last_home_score = 0
        self.last_away_score = 0

    def update_score(self, home_score: int, away_score: int, period: int, time_remaining: str, status: str):
        """Update game score and track momentum"""
        timestamp = time.time()

        # Track score changes
        home_diff = home_score - self.home_score
        away_diff = away_score - self.away_score

        if home_diff > 0 or away_diff > 0:
            self.score_history.append((home_score, away_score, timestamp))
            logger.debug(f"Score update: {self.away_team} {away_score} @ {self.home_team} {home_score}")

        self.home_score = home_score
        self.away_score = away_score
        self.period = period
        self.time_remaining = time_remaining
        self.status = status
        self.last_update = timestamp

    def get_current_run(self) -> Tuple[str, int]:
        """
        Calculate current scoring run
        Returns: (team_name, run_points)
        """
        if len(self.score_history) < 2:
            return ("none", 0)

        # Look at last 10 scoring events
        recent_history = self.score_history[-10:]

        home_run = 0
        away_run = 0

        for i in range(1, len(recent_history)):
            prev_home, prev_away, _ = recent_history[i-1]
            curr_home, curr_away, _ = recent_history[i]

            home_scored = curr_home - prev_home
            away_scored = curr_away - prev_away

            if home_scored > 0 and away_scored == 0:
                home_run += home_scored
                away_run = 0
            elif away_scored > 0 and home_scored == 0:
                away_run += away_scored
                home_run = 0
            else:
                # Both scored or neither scored, reset
                home_run = 0
                away_run = 0

        if home_run >= config.MOMENTUM_RUN_THRESHOLD:
            return (self.home_team, home_run)
        elif away_run >= config.MOMENTUM_RUN_THRESHOLD:
            return (self.away_team, away_run)

        return ("none", 0)

    def get_lead_change(self) -> Optional[Dict]:
        """
        Detect significant lead changes
        Returns: dict with lead change info or None
        """
        if len(self.score_history) < 2:
            return None

        current_lead = self.home_score - self.away_score

        # Check last known lead (from 30 seconds ago if available)
        cutoff_time = time.time() - 30
        old_scores = [h for h in self.score_history if h[2] < cutoff_time]

        if old_scores:
            old_home, old_away, _ = old_scores[-1]
            old_lead = old_home - old_away

            lead_swing = abs(current_lead - old_lead)

            if lead_swing >= config.LEAD_CHANGE_THRESHOLD:
                return {
                    "type": "lead_change",
                    "swing": lead_swing,
                    "old_lead": old_lead,
                    "new_lead": current_lead,
                    "leader": self.home_team if current_lead > 0 else self.away_team
                }

        return None

    def is_close_game(self) -> bool:
        """Check if game is within 5 points"""
        return abs(self.home_score - self.away_score) <= 5


class NBAClient:
    """Client for fetching real-time NBA game data"""

    def __init__(self):
        self.base_url = config.NBA_API_BASE_URL
        self.headers = {}
        if config.NBA_API_KEY:
            # BallDontLie API v1 uses direct API key in Authorization header
            self.headers["Authorization"] = f"{config.NBA_API_KEY}"

        self.games: Dict[str, NBAGame] = {}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._warned_no_key = False

    def _is_game_live(self, status: str) -> bool:
        """
        Check if a game status indicates it's currently in progress

        NBA API returns various status formats:
        - "1st Qtr", "2nd Qtr", "3rd Qtr", "4th Qtr" (quarters)
        - "Halftime" (between 2nd and 3rd quarter)
        - "OT" (overtime)
        - "in_progress", "live" (generic live status)
        - ISO timestamp (e.g., "2026-01-16T00:00:00Z") = scheduled game
        - "Final" = game finished
        """
        if not status:
            return False

        status_lower = status.lower()

        # Check for live indicators
        live_keywords = ["qtr", "quarter", "halftime", "half", "ot", "overtime", "in_progress", "live"]

        for keyword in live_keywords:
            if keyword in status_lower:
                return True

        return False

    def get_live_games(self) -> List[NBAGame]:
        """
        Fetch all currently live NBA games
        Returns: List of NBAGame objects
        """
        try:
            # Get today's games
            response = self.session.get(
                f"{self.base_url}/games",
                params={"dates[]": datetime.now().strftime("%Y-%m-%d")},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            live_games = []

            for game_data in data.get("data", []):
                game_id = str(game_data["id"])
                status = game_data.get("status", "")

                # Only track live games (in progress)
                if not self._is_game_live(status):
                    continue

                # Create or update game object
                if game_id not in self.games:
                    home_team = game_data["home_team"]["full_name"]
                    away_team = game_data["visitor_team"]["full_name"]
                    self.games[game_id] = NBAGame(game_id, home_team, away_team)

                game = self.games[game_id]

                # Update scores
                home_score = game_data.get("home_team_score", 0)
                away_score = game_data.get("visitor_team_score", 0)
                period = game_data.get("period", 0)
                time_remaining = game_data.get("time", "")

                game.update_score(home_score, away_score, period, time_remaining, status)
                live_games.append(game)

            return live_games

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 and not self._warned_no_key:
                logger.error(f"NBA API returned 401 Unauthorized.")
                logger.error("You need a free API key from https://www.balldontlie.io/")
                logger.error("1. Sign up for free at balldontlie.io")
                logger.error("2. Get your API key")
                logger.error("3. Add NBA_API_KEY=your_key to your .env file")
                self._warned_no_key = True
            else:
                logger.error(f"Error fetching live games: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching live games: {e}")
            return []

    def get_game_details(self, game_id: str) -> Optional[Dict]:
        """Get detailed stats for a specific game"""
        try:
            response = self.session.get(
                f"{self.base_url}/games/{game_id}",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching game {game_id}: {e}")
            return None


if __name__ == "__main__":
    # Test the NBA client
    logging.basicConfig(level=logging.DEBUG)
    client = NBAClient()

    print("Fetching live NBA games...")
    games = client.get_live_games()

    if games:
        for game in games:
            print(f"\n{game.away_team} @ {game.home_team}")
            print(f"Score: {game.away_score} - {game.home_score}")
            print(f"Period: {game.period}, Time: {game.time_remaining}")

            team, run = game.get_current_run()
            if run > 0:
                print(f"🔥 {team} on a {run}-0 run!")

            lead_change = game.get_lead_change()
            if lead_change:
                print(f"📊 Lead change: {lead_change}")
    else:
        print("No live games at the moment")
