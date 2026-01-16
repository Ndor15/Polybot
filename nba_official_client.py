"""
NBA Official API Client - Uses stats.nba.com (more permissive)

Provides access to:
- Live game scores and status
- Detailed player box scores (points, assists, rebounds, etc.)
- Real-time player performance tracking
"""
import requests
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import NBAGame class for compatibility
try:
    from nba_client import NBAGame
except ImportError:
    # Define a minimal NBAGame class if import fails
    class NBAGame:
        def __init__(self, game_id: str, home_team: str, away_team: str):
            self.game_id = game_id
            self.home_team = home_team
            self.away_team = away_team
            self.home_score = 0
            self.away_score = 0
            self.period = 0
            self.time_remaining = ""
            self.status = "scheduled"
            self.score_history = []

        def update_score(self, home_score: int, away_score: int, period: int, time_remaining: str, status: str):
            self.home_score = home_score
            self.away_score = away_score
            self.period = period
            self.time_remaining = time_remaining
            self.status = status


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
        self.cache_duration = 10  # Cache for 10 seconds (balance between freshness and VPN latency)

        # Track games for momentum tracking
        self.games_tracker: Dict[str, NBAGame] = {}

    def get_live_games(self) -> List[NBAGame]:
        """
        Fetch all games for today using scoreboard endpoint

        Returns: List of NBAGame objects (compatible with signal_analyzer)
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

            # Retry logic with exponential backoff
            max_retries = 3
            retry_delay = 2  # seconds

            for attempt in range(max_retries):
                try:
                    response = self.session.get(url, params=params, timeout=60)  # Increased timeout to 60s (VPN can be very slow)
                    response.raise_for_status()
                    data = response.json()
                    break  # Success, exit retry loop
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        logger.warning(f"NBA API timeout, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise  # Last attempt failed, raise the exception
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"NBA API error: {e}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise

            games = []

            # Parse scoreboard
            scoreboard = data.get('scoreboard', {})
            game_header = scoreboard.get('games', [])

            for game_data in game_header:
                game_id = game_data.get('gameId', '')

                # Get team info
                home_team = game_data.get('homeTeam', {})
                away_team = game_data.get('awayTeam', {})

                home_name = home_team.get('teamName', '')
                away_name = away_team.get('teamName', '')
                home_score = home_team.get('score', 0)
                away_score = away_team.get('score', 0)

                # Get game status
                game_status = game_data.get('gameStatus', 1)
                period = game_data.get('period', 0)
                game_time = game_data.get('gameClock', '')

                # Status: 1=scheduled, 2=live, 3=final
                if game_status == 2:  # Live game
                    status_text = "live"
                    time_remaining = game_time or f"{period}Q"

                    home_team_full = f"{home_team.get('teamCity', '')} {home_name}".strip()
                    away_team_full = f"{away_team.get('teamCity', '')} {away_name}".strip()

                    # Create or update NBAGame object
                    if game_id in self.games_tracker:
                        game_obj = self.games_tracker[game_id]
                        game_obj.update_score(home_score, away_score, period, time_remaining, status_text)
                    else:
                        game_obj = NBAGame(game_id, home_team_full, away_team_full)
                        game_obj.update_score(home_score, away_score, period, time_remaining, status_text)
                        self.games_tracker[game_id] = game_obj

                    games.append(game_obj)

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

    def get_player_box_scores(self, game_id: str) -> Dict[str, List[Dict]]:
        """
        Fetch detailed player box scores for a specific game

        Args:
            game_id: NBA game ID (10 digits, e.g., '0022300123')

        Returns: Dict with structure:
        {
            'home_players': [{
                'name': str,
                'player_id': str,
                'points': int,
                'assists': int,
                'rebounds': int,
                'steals': int,
                'blocks': int,
                'turnovers': int,
                'field_goals_made': int,
                'field_goals_attempted': int,
                'three_pointers_made': int,
                'minutes': str
            }],
            'away_players': [...]
        }
        """
        # Check cache
        cache_key = f'boxscore_{game_id}'
        now = time.time()
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if now - cached_time < self.cache_duration:
                logger.debug(f"Using cached box score data for game {game_id}")
                return cached_data

        try:
            url = f"{self.base_url}/boxscoretraditionalv3"
            params = {
                'GameID': game_id,
                'StartPeriod': '0',
                'EndPeriod': '14',  # Cover all periods including OT
                'StartRange': '0',
                'EndRange': '55800',  # Full game range
                'RangeType': '2'
            }

            # Retry logic with exponential backoff
            max_retries = 3
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    response = self.session.get(url, params=params, timeout=60)  # Increased timeout to 60s
                    response.raise_for_status()
                    data = response.json()
                    break
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        logger.warning(f"Box score API timeout for game {game_id}, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Box score API error for game {game_id}: {e}, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise

            all_players = []

            # Parse player stats
            # The API returns playerStats as a list of player dictionaries
            player_stats = data.get('boxScoreTraditional', {}).get('playerStats', [])

            for player in player_stats:
                player_data = {
                    'name': f"{player.get('firstName', '')} {player.get('familyName', '')}".strip(),
                    'player_id': str(player.get('personId', '')),
                    'team_id': str(player.get('teamId', '')),
                    'team_name': player.get('teamName', ''),
                    'points': player.get('points', 0),
                    'assists': player.get('assists', 0),
                    'rebounds': player.get('reboundsTotal', 0),
                    'rebounds_offensive': player.get('reboundsOffensive', 0),
                    'rebounds_defensive': player.get('reboundsDefensive', 0),
                    'steals': player.get('steals', 0),
                    'blocks': player.get('blocks', 0),
                    'turnovers': player.get('turnovers', 0),
                    'field_goals_made': player.get('fieldGoalsMade', 0),
                    'field_goals_attempted': player.get('fieldGoalsAttempted', 0),
                    'field_goal_percentage': player.get('fieldGoalsPercentage', 0),
                    'three_pointers_made': player.get('threePointersMade', 0),
                    'three_pointers_attempted': player.get('threePointersAttempted', 0),
                    'three_point_percentage': player.get('threePointersPercentage', 0),
                    'free_throws_made': player.get('freeThrowsMade', 0),
                    'free_throws_attempted': player.get('freeThrowsAttempted', 0),
                    'minutes': player.get('minutes', 'PT00M00.00S'),
                    'plus_minus': player.get('plusMinusPoints', 0),
                    'position': player.get('position', ''),
                    'is_starter': player.get('starter', '0') == '1'
                }

                all_players.append(player_data)

            # Get team stats to determine home/away
            team_stats = data.get('boxScoreTraditional', {}).get('teamStats', [])
            home_team_id = None
            away_team_id = None

            if len(team_stats) >= 2:
                # First team is typically away, second is home in NBA API
                away_team_id = str(team_stats[0].get('teamId', ''))
                home_team_id = str(team_stats[1].get('teamId', ''))

            # Now separate players by team
            home_players = [p for p in all_players if p['team_id'] == home_team_id]
            away_players = [p for p in all_players if p['team_id'] == away_team_id]

            result = {
                'home_players': home_players,
                'away_players': away_players,
                'home_team_id': home_team_id,
                'away_team_id': away_team_id
            }

            # Cache the result
            self.cache[cache_key] = (now, result)

            logger.debug(f"Fetched box scores for game {game_id}: {len(home_players)} home, {len(away_players)} away")
            return result

        except Exception as e:
            logger.error(f"Error fetching box scores for game {game_id}: {e}")

            # Return cached data if available
            if cache_key in self.cache:
                _, cached_data = self.cache[cache_key]
                logger.warning("Returning stale cached box score data due to API error")
                return cached_data

            return {'home_players': [], 'away_players': [], 'home_team_id': None, 'away_team_id': None}

    def get_player_pacing(self, player_stats: Dict, minutes_played: float, period: int) -> Dict[str, float]:
        """
        Calculate if player is on pace for over/under on various stats

        Args:
            player_stats: Player stat dict from get_player_box_scores
            minutes_played: Total minutes played so far
            period: Current period (1-4 for regulation)

        Returns: Dict with projected totals:
        {
            'points_pace': float,  # Projected final points
            'assists_pace': float,
            'rebounds_pace': float,
            'is_on_pace_points': bool,  # If on pace for typical output
            ...
        }
        """
        if minutes_played <= 0:
            return {}

        # Estimate total minutes (assume 36 min for starters, 24 for bench)
        estimated_total_minutes = 36.0 if player_stats.get('is_starter', False) else 24.0

        # If we're in 4Q, use actual pace
        if period >= 4:
            # Game is almost over, use 48 min as total
            estimated_total_minutes = 48.0

        # Calculate pace multiplier
        pace_multiplier = estimated_total_minutes / minutes_played if minutes_played > 0 else 0

        points_pace = player_stats.get('points', 0) * pace_multiplier
        assists_pace = player_stats.get('assists', 0) * pace_multiplier
        rebounds_pace = player_stats.get('rebounds', 0) * pace_multiplier
        steals_pace = player_stats.get('steals', 0) * pace_multiplier
        blocks_pace = player_stats.get('blocks', 0) * pace_multiplier
        threes_pace = player_stats.get('three_pointers_made', 0) * pace_multiplier

        return {
            'points_pace': round(points_pace, 1),
            'assists_pace': round(assists_pace, 1),
            'rebounds_pace': round(rebounds_pace, 1),
            'steals_pace': round(steals_pace, 1),
            'blocks_pace': round(blocks_pace, 1),
            'threes_pace': round(threes_pace, 1),
            'current_points': player_stats.get('points', 0),
            'current_assists': player_stats.get('assists', 0),
            'current_rebounds': player_stats.get('rebounds', 0),
            'pace_multiplier': round(pace_multiplier, 2)
        }


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
