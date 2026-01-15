"""
Player Prop Signal Analyzer

Generates trading signals for player performance markets:
- Points Over/Under
- Assists Over/Under
- Rebounds Over/Under
- Three-Pointers Made Over/Under
- Player Combos (Points + Rebounds + Assists)

Strategies:
1. Hot Hand - Player performing well above pace
2. Cold Hand - Player underperforming, likely to revert
3. Pace Analysis - On track to hit/miss their line
4. Garbage Time - Blowout games = more stats for bench
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PlayerPropSignal:
    """Signal for player prop market"""
    player_name: str
    stat_type: str  # 'points', 'assists', 'rebounds', 'threes'
    market_line: float  # The over/under line
    current_value: float  # Current stat value
    projected_value: float  # Projected final value
    side: str  # 'over' or 'under'
    confidence: float  # 0.0 to 1.0
    reason: str
    period: int
    minutes_played: float
    game_id: str


class PlayerPropAnalyzer:
    """
    Analyzes player performance and generates signals for player prop markets
    """

    def __init__(self, config):
        self.config = config

    def analyze_player_props(
        self,
        player_stats: Dict,
        period: int,
        score_differential: int,
        player_markets: List[Dict]
    ) -> List[PlayerPropSignal]:
        """
        Analyze a player's stats and generate trading signals

        Args:
            player_stats: Player stats from NBA API with pacing data
            period: Current period
            score_differential: Point differential (positive = winning)
            player_markets: Available Polymarket markets for this player

        Returns:
            List of PlayerPropSignal objects
        """
        signals = []

        if not player_stats or period < 1:
            return signals

        player_name = player_stats.get('name', '')
        minutes_played = self._parse_minutes(player_stats.get('minutes', 'PT00M00.00S'))

        # Need meaningful playing time for signals
        if minutes_played < 5.0:
            return signals

        # Get pacing data
        pacing = player_stats.get('pacing', {})
        if not pacing:
            logger.debug(f"No pacing data for {player_name}")
            return signals

        # Analyze each stat type
        for market in player_markets:
            stat_type = self._extract_stat_type(market)
            line = self._extract_line(market)

            if not stat_type or line is None:
                continue

            # Generate signal for this prop
            signal = self._analyze_single_prop(
                player_stats=player_stats,
                pacing=pacing,
                stat_type=stat_type,
                line=line,
                period=period,
                minutes_played=minutes_played,
                score_differential=score_differential,
                market=market
            )

            if signal and signal.confidence >= 0.60:
                signals.append(signal)

        return signals

    def _analyze_single_prop(
        self,
        player_stats: Dict,
        pacing: Dict,
        stat_type: str,
        line: float,
        period: int,
        minutes_played: float,
        score_differential: int,
        market: Dict
    ) -> Optional[PlayerPropSignal]:
        """Analyze a single player prop market"""

        player_name = player_stats.get('name', '')
        game_id = player_stats.get('game_id', '')

        # Map stat type to current value and pace
        stat_map = {
            'points': ('current_points', 'points_pace'),
            'assists': ('current_assists', 'assists_pace'),
            'rebounds': ('current_rebounds', 'rebounds_pace'),
            'threes': ('current_threes', 'threes_pace'),
            'steals': ('current_steals', 'steals_pace'),
            'blocks': ('current_blocks', 'blocks_pace')
        }

        if stat_type not in stat_map:
            return None

        current_key, pace_key = stat_map[stat_type]
        current_value = pacing.get(current_key, 0)
        projected_value = pacing.get(pace_key, 0)

        # Strategy 1: Hot Hand - Already crushing the line
        if period <= 2 and current_value >= line * 0.7:
            # Player already has 70%+ of line in first half
            return PlayerPropSignal(
                player_name=player_name,
                stat_type=stat_type,
                market_line=line,
                current_value=current_value,
                projected_value=projected_value,
                side='over',
                confidence=0.75,
                reason=f"Hot hand: {current_value} {stat_type} in {period}Q (line: {line})",
                period=period,
                minutes_played=minutes_played,
                game_id=game_id
            )

        # Strategy 2: Pace Analysis - On track to smash over
        if projected_value >= line * 1.25:
            # Projected to beat line by 25%+
            confidence = min(0.80, 0.65 + (projected_value - line) / line * 0.3)
            return PlayerPropSignal(
                player_name=player_name,
                stat_type=stat_type,
                market_line=line,
                current_value=current_value,
                projected_value=projected_value,
                side='over',
                confidence=confidence,
                reason=f"Pace: Projected {projected_value} vs line {line}",
                period=period,
                minutes_played=minutes_played,
                game_id=game_id
            )

        # Strategy 3: Late game under - Not enough time left
        if period >= 4 and minutes_played >= 30:
            # In 4Q with 30+ min played, use actual projection
            gap_to_line = line - current_value
            time_remaining_factor = (48 - minutes_played) / 48

            if gap_to_line > projected_value * time_remaining_factor:
                # Not enough time/pace to hit line
                confidence = 0.70
                return PlayerPropSignal(
                    player_name=player_name,
                    stat_type=stat_type,
                    market_line=line,
                    current_value=current_value,
                    projected_value=projected_value,
                    side='under',
                    confidence=confidence,
                    reason=f"Late game under: {current_value}/{line} with {48-minutes_played:.0f}min left",
                    period=period,
                    minutes_played=minutes_played,
                    game_id=game_id
                )

        # Strategy 4: Blowout Bonus - Garbage time stats
        if abs(score_differential) >= 20 and period >= 3:
            # Blowout game, bench players get more minutes
            is_starter = player_stats.get('is_starter', False)

            if not is_starter and current_value >= line * 0.5:
                # Bench player already halfway to line in garbage time
                return PlayerPropSignal(
                    player_name=player_name,
                    stat_type=stat_type,
                    market_line=line,
                    current_value=current_value,
                    projected_value=projected_value,
                    side='over',
                    confidence=0.65,
                    reason=f"Garbage time: Bench player {current_value}/{line} in blowout",
                    period=period,
                    minutes_played=minutes_played,
                    game_id=game_id
                )

        # Strategy 5: Cold Hand Fade - Way below pace, unlikely to recover
        if period >= 3 and projected_value <= line * 0.6:
            # Projected to fall well short of line
            confidence = 0.70
            return PlayerPropSignal(
                player_name=player_name,
                stat_type=stat_type,
                market_line=line,
                current_value=current_value,
                projected_value=projected_value,
                side='under',
                confidence=confidence,
                reason=f"Cold hand: Projected {projected_value} vs line {line}",
                period=period,
                minutes_played=minutes_played,
                game_id=game_id
            )

        return None

    def _extract_stat_type(self, market: Dict) -> Optional[str]:
        """
        Extract stat type from market question

        Examples:
        - "Jaren Jackson Jr.: Points Over 18.5" -> 'points'
        - "Ja Morant: Assists Over 7.5" -> 'assists'
        - "Total Rebounds Over 9.5" -> 'rebounds'
        """
        question = market.get('question', '').lower()

        if 'point' in question:
            return 'points'
        elif 'assist' in question:
            return 'assists'
        elif 'rebound' in question:
            return 'rebounds'
        elif 'three' in question or '3pt' in question or '3-pt' in question:
            return 'threes'
        elif 'steal' in question:
            return 'steals'
        elif 'block' in question:
            return 'blocks'

        return None

    def _extract_line(self, market: Dict) -> Optional[float]:
        """
        Extract the over/under line from market question

        Examples:
        - "Points Over 18.5" -> 18.5
        - "Assists Over 7.5" -> 7.5
        """
        question = market.get('question', '')

        # Look for number patterns
        import re
        numbers = re.findall(r'\d+\.?\d*', question)

        if numbers:
            try:
                return float(numbers[0])
            except:
                pass

        return None

    def _parse_minutes(self, minutes_str: str) -> float:
        """
        Parse ISO 8601 duration format to minutes

        Example: 'PT28M45.00S' -> 28.75
        """
        if not minutes_str or not isinstance(minutes_str, str):
            return 0.0

        try:
            # Format: PT##M##.##S
            import re
            match = re.search(r'PT(\d+)M(\d+(?:\.\d+)?)S', minutes_str)
            if match:
                mins = int(match.group(1))
                secs = float(match.group(2))
                return mins + secs / 60.0
        except:
            pass

        return 0.0


if __name__ == "__main__":
    # Test the analyzer
    logging.basicConfig(level=logging.DEBUG)

    from config import config
    analyzer = PlayerPropAnalyzer(config)

    # Mock player stats
    test_player = {
        'name': 'Ja Morant',
        'points': 12,
        'assists': 5,
        'rebounds': 3,
        'minutes': 'PT18M30.00S',
        'is_starter': True,
        'game_id': '0022300123',
        'pacing': {
            'current_points': 12,
            'current_assists': 5,
            'current_rebounds': 3,
            'points_pace': 24.0,
            'assists_pace': 10.0,
            'rebounds_pace': 6.0,
            'pace_multiplier': 2.0
        }
    }

    # Mock markets
    test_markets = [
        {'question': 'Ja Morant: Points Over 18.5', 'condition_id': '123'},
        {'question': 'Ja Morant: Assists Over 7.5', 'condition_id': '124'},
    ]

    signals = analyzer.analyze_player_props(
        player_stats=test_player,
        period=2,
        score_differential=5,
        player_markets=test_markets
    )

    print(f"\nGenerated {len(signals)} signals:\n")
    for signal in signals:
        print(f"{signal.player_name} - {signal.stat_type.upper()}")
        print(f"  Line: {signal.market_line} | Current: {signal.current_value} | Projected: {signal.projected_value}")
        print(f"  Side: {signal.side.upper()} | Confidence: {signal.confidence:.2f}")
        print(f"  Reason: {signal.reason}")
        print()
