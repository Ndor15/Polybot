"""
Signal Analysis Engine - Detects trading opportunities from NBA game events
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from nba_client import NBAGame
from config import config

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of trading signals"""
    MOMENTUM_RUN = "momentum_run"
    LEAD_CHANGE = "lead_change"
    CLOSE_GAME = "close_game"
    COMEBACK = "comeback"


class SignalDirection(Enum):
    """Trading direction"""
    BUY_HOME = "buy_home"  # Bet on home team winning
    BUY_AWAY = "buy_away"  # Bet on away team winning
    SELL_HOME = "sell_home"  # Bet against home team
    SELL_AWAY = "sell_away"  # Bet against away team


@dataclass
class TradingSignal:
    """Represents a trading opportunity"""
    signal_type: SignalType
    direction: SignalDirection
    confidence: float  # 0.0 to 1.0
    game_id: str
    team: str
    reason: str
    metadata: Dict

    def __repr__(self):
        return f"Signal({self.signal_type.value}, {self.direction.value}, conf={self.confidence:.2f}, {self.reason})"


class SignalAnalyzer:
    """
    Analyzes NBA game events and generates trading signals

    Strategy insights:
    - Momentum runs (8+ points unanswered) often overshoot in betting odds
    - Lead changes create volatility - opportunity to fade the panic
    - Close games in 4th quarter have high variance
    - Teams on comebacks have momentum but odds may overreact
    """

    def __init__(self):
        self.signal_history: List[TradingSignal] = []

    def analyze_game(self, game: NBAGame) -> List[TradingSignal]:
        """
        Analyze a single game and generate trading signals
        Returns: List of trading signals
        """
        signals = []

        # Only analyze live games
        if game.status not in ["in_progress", "live"]:
            return signals

        # Check for momentum run signal
        momentum_signal = self._check_momentum_run(game)
        if momentum_signal:
            signals.append(momentum_signal)

        # Check for lead change signal
        lead_change_signal = self._check_lead_change(game)
        if lead_change_signal:
            signals.append(lead_change_signal)

        # Check for close game opportunities
        close_game_signal = self._check_close_game(game)
        if close_game_signal:
            signals.append(close_game_signal)

        # Check for comeback scenario
        comeback_signal = self._check_comeback(game)
        if comeback_signal:
            signals.append(comeback_signal)

        # Store signals
        self.signal_history.extend(signals)

        return signals

    def _check_momentum_run(self, game: NBAGame) -> Optional[TradingSignal]:
        """
        Detect momentum run opportunities

        Strategy: When a team goes on a big run (8+ points unanswered),
        odds often overreact. We can fade this by betting on the OTHER team
        as the run is likely to slow down.
        """
        team, run_points = game.get_current_run()

        if run_points >= config.MOMENTUM_RUN_THRESHOLD:
            # Fade the run - bet on the OTHER team
            # Because runs eventually stop and odds have overreacted

            is_home_team = (team == game.home_team)

            # Bet AGAINST the team on the run
            if is_home_team:
                direction = SignalDirection.BUY_AWAY
                target_team = game.away_team
            else:
                direction = SignalDirection.BUY_HOME
                target_team = game.home_team

            # Higher run = higher confidence (more overreaction)
            confidence = min(0.5 + (run_points / 20), 0.85)

            return TradingSignal(
                signal_type=SignalType.MOMENTUM_RUN,
                direction=direction,
                confidence=confidence,
                game_id=game.game_id,
                team=target_team,
                reason=f"Fading {team}'s {run_points}-0 run",
                metadata={
                    "run_points": run_points,
                    "running_team": team,
                    "period": game.period
                }
            )

        return None

    def _check_lead_change(self, game: NBAGame) -> Optional[TradingSignal]:
        """
        Detect lead change opportunities

        Strategy: When lead changes rapidly (5+ point swing),
        odds panic. We can fade the panic by betting on the team
        that just LOST the lead, as variance will revert.
        """
        lead_change = game.get_lead_change()

        if not lead_change:
            return None

        swing = lead_change["swing"]
        new_leader = lead_change["leader"]

        # Bet on the team that just LOST the lead (contrarian)
        if new_leader == game.home_team:
            direction = SignalDirection.BUY_AWAY
            target_team = game.away_team
        else:
            direction = SignalDirection.BUY_HOME
            target_team = game.home_team

        # Bigger swing = higher confidence
        confidence = min(0.4 + (swing / 30), 0.75)

        return TradingSignal(
            signal_type=SignalType.LEAD_CHANGE,
            direction=direction,
            confidence=confidence,
            game_id=game.game_id,
            team=target_team,
            reason=f"Fading lead change: {new_leader} took lead with {swing}pt swing",
            metadata=lead_change
        )

    def _check_close_game(self, game: NBAGame) -> Optional[TradingSignal]:
        """
        Detect close game opportunities in 4th quarter

        Strategy: In close 4th quarter games, bet on the HOME team
        as they have home court advantage and odds are volatile.
        """
        # Only in 4th quarter
        if game.period != 4:
            return None

        if not game.is_close_game():
            return None

        # Small home court edge
        direction = SignalDirection.BUY_HOME
        confidence = 0.55  # Slight edge

        return TradingSignal(
            signal_type=SignalType.CLOSE_GAME,
            direction=direction,
            confidence=confidence,
            game_id=game.game_id,
            team=game.home_team,
            reason=f"Close 4th quarter game, home court advantage",
            metadata={
                "score_diff": abs(game.home_score - game.away_score),
                "period": game.period
            }
        )

    def _check_comeback(self, game: NBAGame) -> Optional[TradingSignal]:
        """
        Detect comeback opportunities

        Strategy: If a team was down big and has cut lead significantly,
        they have momentum. But odds may overreact, so we fade slightly.
        """
        if len(game.score_history) < 5:
            return None

        # Check if there was a big deficit earlier
        early_scores = game.score_history[:len(game.score_history)//2]
        if not early_scores:
            return None

        max_deficit_home = 0
        max_deficit_away = 0

        for home_score, away_score, _ in early_scores:
            deficit = home_score - away_score
            if deficit < max_deficit_home:
                max_deficit_home = deficit
            if -deficit < max_deficit_away:
                max_deficit_away = -deficit

        current_diff = game.home_score - game.away_score

        # Check if home team was down 10+ and now within 5
        if max_deficit_home <= -10 and current_diff >= -5:
            # Home team comeback
            # Fade it slightly - bet away
            return TradingSignal(
                signal_type=SignalType.COMEBACK,
                direction=SignalDirection.BUY_AWAY,
                confidence=0.60,
                game_id=game.game_id,
                team=game.away_team,
                reason=f"{game.home_team} comeback from {abs(max_deficit_home)} down - fading",
                metadata={
                    "max_deficit": abs(max_deficit_home),
                    "current_diff": current_diff
                }
            )

        # Check if away team was down 10+ and now within 5
        if max_deficit_away <= -10 and current_diff <= 5:
            # Away team comeback
            return TradingSignal(
                signal_type=SignalType.COMEBACK,
                direction=SignalDirection.BUY_HOME,
                confidence=0.60,
                game_id=game.game_id,
                team=game.home_team,
                reason=f"{game.away_team} comeback from {abs(max_deficit_away)} down - fading",
                metadata={
                    "max_deficit": abs(max_deficit_away),
                    "current_diff": current_diff
                }
            )

        return None

    def filter_signals(self, signals: List[TradingSignal], min_confidence: float = 0.6) -> List[TradingSignal]:
        """
        Filter signals by minimum confidence threshold
        """
        return [s for s in signals if s.confidence >= min_confidence]

    def get_best_signal(self, signals: List[TradingSignal]) -> Optional[TradingSignal]:
        """
        Get the highest confidence signal
        """
        if not signals:
            return None

        return max(signals, key=lambda s: s.confidence)


if __name__ == "__main__":
    # Test the signal analyzer
    logging.basicConfig(level=logging.DEBUG)

    # Create a mock game
    game = NBAGame("test_123", "Los Angeles Lakers", "Boston Celtics")
    game.update_score(85, 80, 4, "5:30", "in_progress")

    # Simulate a run
    game.score_history = [
        (75, 80, 1000),
        (77, 80, 1005),
        (79, 80, 1010),
        (81, 80, 1015),
        (83, 80, 1020),
        (85, 80, 1025),
    ]

    analyzer = SignalAnalyzer()
    signals = analyzer.analyze_game(game)

    print(f"\nGenerated {len(signals)} signals:")
    for signal in signals:
        print(f"  {signal}")

    best = analyzer.get_best_signal(signals)
    if best:
        print(f"\n🎯 Best signal: {best}")
