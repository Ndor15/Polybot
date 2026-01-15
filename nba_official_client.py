"""
NBA Official API Client - Uses stats.nba.com (more permissive)
"""
import requests
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NBAOfficialClient:
    """
    Client for NBA Official Stats API (stats.nba.com)

    This is more permissive than BallDontLie and doesn't require API key.
    """

    def __init__(self):
        self.base_url = "https://stats.nba.com/stats"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://stats.nba.com/',
            'x-nba-stats-origin': 'stats',
            'x-nba-stats-token': 'true'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Cache to avoid hammering API
        self.cache = {}
        self.cache_duration = 5  # Cache for 5 seconds

    def get_live_games(self) -> List[Dict]:
        """
        Fetch all games for today using scoreboard endpoint

        Returns: List of game dicts with structure:
        {
            'game_id': str,
            'home_team': str,
            'away_team': str,
            'home_score': int,
            'away_score': int,
            'period': int,
            'status': str,
            'time_remaining': str
        }
        """
        # Check cache
        now = time.time()
        if 'scoreboard' in self.cache:
            cached_time, cached_data = self.cache['scoreboard']
            if now - cached_time < self.cache_duration:
                logger.debug("Using cached scoreboard data")
                return cached_data

        try:
            # Get today's scoreboard
            today = datetime.now().strftime("%Y-%m-%d")

            url = f"{self.base_url}/scoreboardv3"
            params = {
                'GameDate': today,
                'LeagueID': '00'
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            games = []

            # Parse scoreboard
            scoreboard = data.get('scoreboard', {})
            game_header = scoreboard.get('games', [])

            for game in game_header:
                game_id = game.get('gameId', '')

                # Get team info
                home_team = game.get('homeTeam', {})
                away_team = game.get('awayTeam', {})

                home_name = home_team.get('teamName', '')
                away_name = away_team.get('teamName', '')
                home_score = home_team.get('score', 0)
                away_score = away_team.get('score', 0)

                # Get game status
                game_status = game.get('gameStatus', 1)
                period = game.get('period', 0)
                game_time = game.get('gameClock', '')

                # Status: 1=scheduled, 2=live, 3=final
                if game_status == 2:  # Live game
                    status_text = f"Period {period}"
                    if game_time:
                        status_text = f"{period}Q {game_time}"

                    games.append({
                        'game_id': game_id,
                        'home_team': f"{home_team.get('teamCity', '')} {home_name}",
                        'away_team': f"{away_team.get('teamCity', '')} {away_name}",
                        'home_score': home_score,
                        'away_score': away_score,
                        'period': period,
                        'status': status_text,
                        'time_remaining': game_time
                    })

            # Cache the result
            self.cache['scoreboard'] = (now, games)

            logger.debug(f"Fetched {len(games)} live games from NBA Official API")
            return games

        except Exception as e:
            logger.error(f"Error fetching from NBA Official API: {e}")

            # Return cached data if available
            if 'scoreboard' in self.cache:
                _, cached_data = self.cache['scoreboard']
                logger.warning("Returning stale cached data due to API error")
                return cached_data

            return []


if __name__ == "__main__":
    # Test the official API
    logging.basicConfig(level=logging.DEBUG)

    client = NBAOfficialClient()

    print("Testing NBA Official API...\n")
    games = client.get_live_games()

    if games:
        print(f"Found {len(games)} live games:\n")
        for game in games:
            print(f"{game['away_team']} @ {game['home_team']}")
            print(f"  Score: {game['away_score']}-{game['home_score']}")
            print(f"  Status: {game['status']}")
            print()
    else:
        print("No live games found")
