"""
Market Matcher - Intelligent matching between NBA games and Polymarket markets

Uses fuzzy matching, team name normalization, and timing to find the right markets.
"""
import logging
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import re
from datetime import datetime
from nba_client import NBAGame

logger = logging.getLogger(__name__)


class TeamNameNormalizer:
    """Normalizes NBA team names for better matching"""

    # Common team name variations
    TEAM_ABBREVIATIONS = {
        "Lakers": ["LAL", "LA Lakers", "Los Angeles Lakers", "L.A. Lakers", "Los Angeles", "LA", "L.A."],
        "Celtics": ["BOS", "Boston Celtics", "Boston"],
        "Warriors": ["GSW", "GS Warriors", "Golden State Warriors", "Golden State", "GS"],
        "Heat": ["MIA", "Miami Heat", "Miami"],
        "Knicks": ["NYK", "NY Knicks", "New York Knicks", "New York"],
        "Bulls": ["CHI", "Chicago Bulls", "Chicago"],
        "Nets": ["BKN", "Brooklyn Nets", "Brooklyn"],
        "76ers": ["PHI", "Philadelphia 76ers", "Sixers", "Philadelphia"],
        "Bucks": ["MIL", "Milwaukee Bucks", "Milwaukee"],
        "Clippers": ["LAC", "LA Clippers", "Los Angeles Clippers", "L.A. Clippers"],
        "Nuggets": ["DEN", "Denver Nuggets", "Denver"],
        "Mavericks": ["DAL", "Dallas Mavericks", "Mavs", "Dallas"],
        "Suns": ["PHX", "Phoenix Suns", "Phoenix"],
        "Grizzlies": ["MEM", "Memphis Grizzlies", "Memphis"],
        "Pelicans": ["NOP", "New Orleans Pelicans", "New Orleans"],
        "Spurs": ["SAS", "San Antonio Spurs", "San Antonio"],
        "Rockets": ["HOU", "Houston Rockets", "Houston"],
        "Thunder": ["OKC", "Oklahoma City Thunder", "Oklahoma City", "OKC"],
        "Jazz": ["UTA", "Utah Jazz", "Utah"],
        "Trail Blazers": ["POR", "Portland Trail Blazers", "Blazers", "Portland"],
        "Kings": ["SAC", "Sacramento Kings", "Sacramento"],
        "Timberwolves": ["MIN", "Minnesota Timberwolves", "T-Wolves", "Wolves", "Minnesota"],
        "Pacers": ["IND", "Indiana Pacers", "Indiana"],
        "Cavaliers": ["CLE", "Cleveland Cavaliers", "Cavs", "Cleveland"],
        "Hawks": ["ATL", "Atlanta Hawks", "Atlanta"],
        "Hornets": ["CHA", "Charlotte Hornets", "Charlotte"],
        "Magic": ["ORL", "Orlando Magic", "Orlando"],
        "Pistons": ["DET", "Detroit Pistons", "Detroit"],
        "Wizards": ["WAS", "Washington Wizards", "Washington"],
        "Raptors": ["TOR", "Toronto Raptors", "Toronto"],
    }

    # Reverse mapping: variation -> canonical name
    _REVERSE_MAP = {}

    @classmethod
    def _build_reverse_map(cls):
        """Build reverse lookup map"""
        if not cls._REVERSE_MAP:
            for canonical, variations in cls.TEAM_ABBREVIATIONS.items():
                cls._REVERSE_MAP[canonical.lower()] = canonical
                for variant in variations:
                    cls._REVERSE_MAP[variant.lower()] = canonical

    @classmethod
    def normalize(cls, team_name: str) -> str:
        """
        Normalize a team name to canonical form

        Examples:
            "LAL" -> "Lakers"
            "Los Angeles Lakers" -> "Lakers"
            "LA Lakers" -> "Lakers"
        """
        cls._build_reverse_map()

        # Clean the name
        clean_name = team_name.strip()

        # Try exact match
        if clean_name.lower() in cls._REVERSE_MAP:
            return cls._REVERSE_MAP[clean_name.lower()]

        # Try partial match
        for variant, canonical in cls._REVERSE_MAP.items():
            if variant in clean_name.lower() or clean_name.lower() in variant:
                return canonical

        # Return original if no match
        return clean_name

    @classmethod
    def get_all_variations(cls, canonical_name: str) -> List[str]:
        """Get all variations of a team name"""
        return cls.TEAM_ABBREVIATIONS.get(canonical_name, [canonical_name])


class MarketMatcher:
    """
    Matches NBA games with Polymarket markets

    Strategies:
    1. Team name matching (fuzzy + normalized)
    2. Timing-based matching (game start times)
    3. Market question parsing
    """

    def __init__(self):
        self.normalizer = TeamNameNormalizer()
        self.cached_matches: Dict[str, str] = {}  # game_id -> market_id

    def match_game_to_market(
        self,
        game: NBAGame,
        markets: List[Dict]
    ) -> Optional[Dict]:
        """
        Find the best matching market for a NBA game

        Args:
            game: NBAGame object
            markets: List of Polymarket market objects

        Returns: Best matching market or None
        """
        # Check cache first
        if game.game_id in self.cached_matches:
            market_id = self.cached_matches[game.game_id]
            market = next((m for m in markets if m.get("condition_id") == market_id), None)
            if market:
                return market

        best_match = None
        best_score = 0.0

        # Normalize team names
        home_norm = self.normalizer.normalize(game.home_team)
        away_norm = self.normalizer.normalize(game.away_team)

        for market in markets:
            score = self._calculate_match_score(game, market, home_norm, away_norm)

            if score > best_score and score > 0.6:  # Minimum confidence threshold
                best_score = score
                best_match = market

        if best_match:
            # Cache the match
            self.cached_matches[game.game_id] = best_match.get("condition_id", "")
            logger.info(f"Matched game {away_norm} @ {home_norm} to market (confidence: {best_score:.2f})")

        return best_match

    def _calculate_match_score(
        self,
        game: NBAGame,
        market: Dict,
        home_norm: str,
        away_norm: str
    ) -> float:
        """
        Calculate match score between game and market

        Returns: Score from 0.0 (no match) to 1.0 (perfect match)
        """
        score = 0.0

        # Extract market information
        question = market.get("question", "").lower()
        description = market.get("description", "").lower()
        title = market.get("title", "").lower()

        # Combine all text
        market_text = f"{question} {description} {title}"

        # Check if both team names appear in market text
        home_found = self._team_in_text(home_norm, market_text)
        away_found = self._team_in_text(away_norm, market_text)

        if home_found and away_found:
            score += 0.8  # Strong signal

        elif home_found or away_found:
            score += 0.3  # Weak signal

        # Check for common betting phrases
        if any(phrase in question for phrase in ["win", "winner", "match winner", "to win"]):
            score += 0.2

        return min(score, 1.0)

    def _team_in_text(self, team_canonical: str, text: str) -> bool:
        """Check if team name (or any variation) appears in text"""
        # Check canonical name
        if team_canonical.lower() in text:
            return True

        # Check all variations
        variations = self.normalizer.get_all_variations(team_canonical)
        for variant in variations:
            if variant.lower() in text:
                return True

        return False

    def find_outcome_for_team(
        self,
        market: Dict,
        team_name: str,
        bet_on_team: bool = True
    ) -> Optional[str]:
        """
        New version compatible with Polymarket CLOB formats:
        - outcomes can be list of dicts
        - or list of strings ("Yes","No")
        - or missing names
        """
        outcomes = market.get("outcomes", [])

        if not outcomes:
            return None

        # Normalize team name
        team_norm = self.normalizer.normalize(team_name).lower()

        # Convert outcomes into (name, token_id) list
        normalized_outcomes = []
        for outcome in outcomes:
            if isinstance(outcome, dict):
                o_name = outcome.get("name") or outcome.get("label") or ""
                o_token = outcome.get("token_id") or outcome.get("tokenId")
            else:
                # outcome is a string
                o_name = str(outcome)
                # tokenId stored at market level
                o_token = None

            normalized_outcomes.append((o_name, o_token))

        # Debug logging
        logger.info(f"DEBUG: Looking for team '{team_name}' (normalized: '{team_norm}')")
        logger.info(f"DEBUG: Market outcomes: {[o[0] for o in normalized_outcomes]}")

        # Strategy 1: match full team name inside outcome name
        for o_name, _ in normalized_outcomes:
            if team_norm in o_name.lower():
                logger.info(f"DEBUG: Matched '{team_norm}' in outcome '{o_name}'")
                return o_name if bet_on_team else self._get_opposite_outcome(normalized_outcomes, o_name)

        # Strategy 1.5: Try matching just team nickname or city name
        # e.g., "San Antonio Spurs" → try "spurs" or "san antonio"
        team_parts = team_name.lower().split()
        for part in team_parts:
            if len(part) > 3:  # Skip short words like "LA"
                for o_name, _ in normalized_outcomes:
                    if part in o_name.lower():
                        logger.info(f"DEBUG: Matched part '{part}' in outcome '{o_name}'")
                        return o_name if bet_on_team else self._get_opposite_outcome(normalized_outcomes, o_name)

        # Strategy 2: Yes/No markets
        outcome_names = [o[0] for o in normalized_outcomes]

        if len(outcome_names) == 2 and {"Yes", "No"} <= set([n.capitalize() for n in outcome_names]):
            question = market.get("question", "").lower()

            # If question mentions the team → Yes = team wins
            if team_norm in question:
                return "Yes" if bet_on_team else "No"

            # Otherwise default: Yes = home team
            return "Yes" if bet_on_team else "No"

        # Strategy 3: fallback → first outcome
        if normalized_outcomes:
            first_name = normalized_outcomes[0][0]
            return first_name if bet_on_team else self._get_opposite_outcome(normalized_outcomes, first_name)

        return None

    def _get_opposite_outcome(self, outcomes: List[tuple], outcome_name: str) -> Optional[str]:
        """
        outcomes is list of (name, tokenId)
        """
        if len(outcomes) != 2:
            return None

        for o_name, _ in outcomes:
            if o_name != outcome_name:
                return o_name

        return None

    def get_token_id_for_team(
        self,
        market: Dict,
        team_name: str,
        bet_on_team: bool = True
    ) -> Optional[str]:
        """
        New version compatible with Polymarket CLOB 2025/2026.
        Handles:
        - market["outcomes"] list of dicts
        - list of strings
        - yesTokenId / noTokenId
        - tokenId in outcome dicts
        """
        outcome_name = self.find_outcome_for_team(market, team_name, bet_on_team)

        if not outcome_name:
            return None

        # 1. Try inside outcomes array
        outcomes = market.get("outcomes", [])
        for outcome in outcomes:
            if isinstance(outcome, dict):
                if outcome.get("name") == outcome_name or outcome.get("label") == outcome_name:
                    return outcome.get("token_id") or outcome.get("tokenId")

        # 2. Try Yes/No fields (modern Polymarket format)
        lower = outcome_name.lower()

        if lower == "yes":
            return (
                market.get("yesTokenId")
                or market.get("token_id_yes")
                or market.get("yes_token_id")
                or market.get("yesId")
            )

        if lower == "no":
            return (
                market.get("noTokenId")
                or market.get("token_id_no")
                or market.get("no_token_id")
                or market.get("noId")
            )

        # 3. Fallback: return first available token
        # Sometimes they store tokens at top-level under "tokens"
        if "tokens" in market:
            if isinstance(market["tokens"], list) and len(market["tokens"]) >= 1:
                return market["tokens"][0].get("token_id")

        return None

    def find_player_prop_markets(
        self,
        game: NBAGame,
        player_name: str,
        markets: List[Dict]
    ) -> List[Dict]:
        """
        Find all player prop markets for a specific player in a game

        Args:
            game: NBAGame object
            player_name: Player name (e.g., "Ja Morant")
            markets: List of all Polymarket markets

        Returns: List of markets for this player (points, assists, rebounds, etc.)
        """
        player_markets = []

        # Normalize team names for filtering
        home_norm = self.normalizer.normalize(game.home_team)
        away_norm = self.normalizer.normalize(game.away_team)

        # Clean player name variations
        player_parts = player_name.split()
        player_first = player_parts[0] if len(player_parts) > 0 else ""
        player_last = player_parts[-1] if len(player_parts) > 0 else ""

        for market in markets:
            question = market.get("question", "")
            description = market.get("description", "")
            title = market.get("title", "")

            # Check if this is a player prop (contains player name)
            market_text = f"{question} {description} {title}".lower()

            # Must contain player name
            player_in_market = (
                player_name.lower() in market_text or
                (player_first.lower() in market_text and player_last.lower() in market_text)
            )

            if not player_in_market:
                continue

            # Must be related to the game (has one of the team names)
            game_in_market = (
                self._team_in_text(home_norm, market_text) or
                self._team_in_text(away_norm, market_text)
            )

            if not game_in_market:
                # If no team found, still include if it's clearly a prop market
                # (has stat keywords like "points", "assists", "rebounds")
                if not any(word in market_text for word in ["point", "assist", "rebound", "three", "block", "steal"]):
                    continue

            # Must be a prop market (has stat keywords or "over"/"under")
            is_prop_market = any(word in question.lower() for word in [
                "point", "assist", "rebound", "over", "under",
                "three", "block", "steal", "turno", "pra"  # PRA = Points+Rebounds+Assists
            ])

            if is_prop_market:
                player_markets.append(market)

        logger.debug(f"Found {len(player_markets)} prop markets for {player_name}")
        return player_markets

    def get_all_player_names_from_markets(self, markets: List[Dict]) -> List[str]:
        """
        Extract all unique player names from prop markets

        Returns: List of player names mentioned in markets
        """
        player_names = set()

        for market in markets:
            question = market.get("question", "")

            # Look for player name patterns
            # Typically: "FirstName LastName: Stat Over X"
            import re
            match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+):\s*', question)
            if match:
                player_names.add(match.group(1).strip())

        return sorted(list(player_names))

    def get_token_id_for_prop_outcome(
        self,
        market: Dict,
        side: str  # 'over' or 'under'
    ) -> Optional[str]:
        """
        Get token ID for over/under outcome in a prop market

        Args:
            market: Market dict
            side: 'over' or 'under'

        Returns: Token ID for the specified side
        """
        outcomes = market.get("outcomes", [])

        if not outcomes:
            return None

        # Look for outcome matching the side
        for outcome in outcomes:
            outcome_name = outcome.get("name", "").lower()

            if side.lower() in outcome_name or (side == 'over' and 'yes' in outcome_name):
                return outcome.get("token_id")

        # If not found, default behavior
        if len(outcomes) >= 2:
            # Assume first outcome is 'over' or 'yes'
            return outcomes[0 if side == 'over' else 1].get("token_id")

        return None


if __name__ == "__main__":
    # Test the matcher
    logging.basicConfig(level=logging.DEBUG)

    # Test normalizer
    normalizer = TeamNameNormalizer()

    test_names = [
        "LAL",
        "Los Angeles Lakers",
        "LA Lakers",
        "Lakers",
        "BOS",
        "Boston Celtics",
        "GSW"
    ]

    print("=== Team Name Normalization ===")
    for name in test_names:
        normalized = normalizer.normalize(name)
        print(f"{name:25} -> {normalized}")

    # Test matcher
    print("\n=== Market Matching ===")

    # Mock game
    from nba_client import NBAGame
    game = NBAGame("test_123", "Los Angeles Lakers", "Boston Celtics")
    game.home_score = 100
    game.away_score = 98

    # Mock market
    mock_market = {
        "condition_id": "market_456",
        "question": "Will the Lakers win against the Celtics?",
        "description": "Los Angeles Lakers vs Boston Celtics",
        "title": "Lakers vs Celtics",
        "outcomes": [
            {"name": "Yes", "token_id": "token_yes"},
            {"name": "No", "token_id": "token_no"}
        ]
    }

    matcher = MarketMatcher()
    matched = matcher.match_game_to_market(game, [mock_market])

    if matched:
        print(f"✅ Matched game to market: {matched['question']}")

        # Find outcome for Lakers
        outcome = matcher.find_outcome_for_team(matched, "Lakers", bet_on_team=True)
        print(f"   Bet ON Lakers: {outcome}")

        outcome = matcher.find_outcome_for_team(matched, "Lakers", bet_on_team=False)
        print(f"   Bet AGAINST Lakers: {outcome}")
    else:
        print("❌ No match found")
