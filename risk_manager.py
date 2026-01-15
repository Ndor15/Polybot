"""
Risk Manager - Controls position sizing and portfolio risk
"""
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass
from signal_analyzer import TradingSignal
from polymarket_client import Position
from config import config

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Current risk metrics for the portfolio"""
    total_positions: int
    total_exposure_usdc: float
    total_pnl_usdc: float
    total_pnl_percentage: float
    largest_position_usdc: float
    positions_at_risk: int  # Positions near stop loss


class RiskManager:
    """
    Manages trading risk and position sizing

    Risk controls:
    1. Maximum concurrent positions
    2. Position size limits
    3. Total exposure limits
    4. Correlation limits (no duplicate signals on same game)
    5. Minimum signal confidence
    """

    def __init__(self, max_total_exposure_usdc: float = 50.0):
        self.max_total_exposure_usdc = max_total_exposure_usdc
        self.min_signal_confidence = 0.6
        self.trades_executed = 0
        self.trades_won = 0
        self.trades_lost = 0
        self.total_pnl = 0.0

    def can_open_position(
        self,
        signal: TradingSignal,
        positions: List[Position],
        available_balance: Optional[float] = None
    ) -> tuple[bool, str]:
        """
        Check if it's safe to open a new position

        Returns: (can_open, reason)
        """
        # Check max concurrent positions
        if len(positions) >= config.MAX_CONCURRENT_TRADES:
            return False, f"Max concurrent positions reached ({config.MAX_CONCURRENT_TRADES})"

        # Check signal confidence
        if signal.confidence < self.min_signal_confidence:
            return False, f"Signal confidence too low: {signal.confidence:.2f} < {self.min_signal_confidence}"

        # Check for duplicate game exposure
        for position in positions:
            if position.game_id == signal.game_id:
                return False, f"Already have position on game {signal.game_id}"

        # Check total exposure
        current_exposure = sum(p.size for p in positions)
        if current_exposure + config.TRADE_SIZE_USDC > self.max_total_exposure_usdc:
            return False, f"Total exposure limit reached: ${current_exposure:.2f}"

        # Check available balance if provided
        if available_balance is not None:
            if available_balance < config.TRADE_SIZE_USDC:
                return False, f"Insufficient balance: ${available_balance:.2f} < ${config.TRADE_SIZE_USDC}"

        return True, "OK"

    def calculate_position_size(self, signal: TradingSignal, available_balance: float) -> float:
        """
        Calculate optimal position size based on signal confidence and risk

        Uses Kelly Criterion-inspired sizing:
        - Higher confidence = larger size (up to max)
        - Lower confidence = smaller size
        """
        base_size = config.TRADE_SIZE_USDC

        # Scale by confidence (0.6 confidence = 60% of base, 0.9 = 100% of base)
        confidence_multiplier = (signal.confidence - 0.5) / 0.4  # Normalize 0.5-0.9 to 0-1
        confidence_multiplier = max(0.5, min(1.0, confidence_multiplier))

        position_size = base_size * confidence_multiplier

        # Don't exceed available balance
        position_size = min(position_size, available_balance * 0.2)  # Max 20% of balance per trade

        return round(position_size, 2)

    def get_risk_metrics(self, positions: List[Position]) -> RiskMetrics:
        """Calculate current portfolio risk metrics"""
        if not positions:
            return RiskMetrics(
                total_positions=0,
                total_exposure_usdc=0.0,
                total_pnl_usdc=0.0,
                total_pnl_percentage=0.0,
                largest_position_usdc=0.0,
                positions_at_risk=0
            )

        total_exposure = sum(p.size for p in positions)
        total_pnl = sum(p.get_pnl() for p in positions)
        total_pnl_pct = (total_pnl / total_exposure * 100) if total_exposure > 0 else 0.0
        largest_position = max(p.size for p in positions)

        # Count positions near stop loss (within 1% of SL)
        at_risk = sum(
            1 for p in positions
            if p.get_pnl_percentage() <= -(config.STOP_LOSS_PERCENTAGE - 1.0)
        )

        return RiskMetrics(
            total_positions=len(positions),
            total_exposure_usdc=total_exposure,
            total_pnl_usdc=total_pnl,
            total_pnl_percentage=total_pnl_pct,
            largest_position_usdc=largest_position,
            positions_at_risk=at_risk
        )

    def record_trade_result(self, position: Position, reason: str):
        """Record the outcome of a closed trade"""
        self.trades_executed += 1
        pnl = position.get_pnl()
        self.total_pnl += pnl

        if pnl > 0:
            self.trades_won += 1
            logger.info(f"✅ Trade WIN: +${pnl:.2f} ({position.get_pnl_percentage():.2f}%) - {reason}")
        else:
            self.trades_lost += 1
            logger.info(f"❌ Trade LOSS: ${pnl:.2f} ({position.get_pnl_percentage():.2f}%) - {reason}")

    def get_performance_stats(self) -> Dict:
        """Get trading performance statistics"""
        win_rate = (self.trades_won / self.trades_executed * 100) if self.trades_executed > 0 else 0.0
        avg_pnl = self.total_pnl / self.trades_executed if self.trades_executed > 0 else 0.0

        return {
            "trades_executed": self.trades_executed,
            "trades_won": self.trades_won,
            "trades_lost": self.trades_lost,
            "win_rate": win_rate,
            "total_pnl": self.total_pnl,
            "avg_pnl_per_trade": avg_pnl
        }

    def should_pause_trading(self, positions: List[Position]) -> tuple[bool, str]:
        """
        Check if trading should be paused due to risk conditions

        Pause conditions:
        - Too many losing positions
        - Total drawdown exceeds threshold
        """
        if not positions:
            return False, ""

        metrics = self.get_risk_metrics(positions)

        # Pause if total portfolio down more than 10%
        if metrics.total_pnl_percentage < -10.0:
            return True, f"Portfolio drawdown too high: {metrics.total_pnl_percentage:.2f}%"

        # Pause if too many positions at risk
        if metrics.positions_at_risk >= config.MAX_CONCURRENT_TRADES:
            return True, f"All positions at risk of stop loss"

        return False, ""

    def display_metrics(self, positions: List[Position]):
        """Display current risk metrics"""
        metrics = self.get_risk_metrics(positions)
        stats = self.get_performance_stats()

        print("\n=== Portfolio Metrics ===")
        print(f"Active Positions: {metrics.total_positions}/{config.MAX_CONCURRENT_TRADES}")
        print(f"Total Exposure: ${metrics.total_exposure_usdc:.2f}")
        print(f"Current P&L: ${metrics.total_pnl_usdc:.2f} ({metrics.total_pnl_percentage:.2f}%)")
        print(f"Positions at Risk: {metrics.positions_at_risk}")

        print("\n=== Trading Statistics ===")
        print(f"Trades Executed: {stats['trades_executed']}")
        print(f"Win Rate: {stats['win_rate']:.1f}% ({stats['trades_won']}W / {stats['trades_lost']}L)")
        print(f"Total P&L: ${stats['total_pnl']:.2f}")
        print(f"Avg P&L per Trade: ${stats['avg_pnl_per_trade']:.2f}")
        print("========================\n")


if __name__ == "__main__":
    # Test the risk manager
    logging.basicConfig(level=logging.DEBUG)

    from signal_analyzer import TradingSignal, SignalType, SignalDirection

    manager = RiskManager(max_total_exposure_usdc=50.0)

    # Test position size calculation
    signal = TradingSignal(
        signal_type=SignalType.MOMENTUM_RUN,
        direction=SignalDirection.BUY_HOME,
        confidence=0.75,
        game_id="test_123",
        team="Lakers",
        reason="Test signal",
        metadata={}
    )

    size = manager.calculate_position_size(signal, available_balance=100.0)
    print(f"Position size for 0.75 confidence: ${size:.2f}")

    # Test can_open_position
    can_open, reason = manager.can_open_position(signal, [], available_balance=100.0)
    print(f"Can open position: {can_open} - {reason}")
