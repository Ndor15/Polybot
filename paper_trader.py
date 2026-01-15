"""
Paper Trading Mode - Test strategies without risking real money

Simulates real trading with virtual balance and realistic fills.
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import time
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PaperPosition:
    """Paper trading position"""
    position_id: str
    token_id: str
    side: str
    size: float
    entry_price: float
    current_price: float
    entry_time: float
    game_id: Optional[str]
    team: str

    def get_pnl(self) -> float:
        """Calculate P&L"""
        if self.side == "BUY":
            return (self.current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - self.current_price) * self.size

    def get_pnl_percentage(self) -> float:
        """Calculate P&L percentage"""
        pnl = self.get_pnl()
        return (pnl / self.size) * 100 if self.size > 0 else 0.0


@dataclass
class PaperTrade:
    """Record of a completed paper trade"""
    trade_id: str
    token_id: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_percentage: float
    entry_time: float
    exit_time: float
    duration_seconds: float
    exit_reason: str
    game_id: Optional[str] = None
    team: str = ""


@dataclass
class PaperAccount:
    """Paper trading account state"""
    starting_balance: float
    current_balance: float
    total_pnl: float = 0.0
    trades: List[PaperTrade] = field(default_factory=list)
    positions: Dict[str, PaperPosition] = field(default_factory=dict)

    def get_total_exposure(self) -> float:
        """Get total capital in open positions"""
        return sum(p.size for p in self.positions.values())

    def get_available_balance(self) -> float:
        """Get available balance for new trades"""
        return self.current_balance - self.get_total_exposure()

    def get_win_rate(self) -> float:
        """Calculate win rate percentage"""
        if not self.trades:
            return 0.0
        winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        return (winning_trades / len(self.trades)) * 100

    def get_avg_win(self) -> float:
        """Average winning trade P&L"""
        winning_trades = [t.pnl for t in self.trades if t.pnl > 0]
        return sum(winning_trades) / len(winning_trades) if winning_trades else 0.0

    def get_avg_loss(self) -> float:
        """Average losing trade P&L"""
        losing_trades = [t.pnl for t in self.trades if t.pnl < 0]
        return sum(losing_trades) / len(losing_trades) if losing_trades else 0.0

    def get_sharpe_ratio(self) -> float:
        """Simple Sharpe ratio (returns / std deviation)"""
        if len(self.trades) < 2:
            return 0.0

        returns = [t.pnl_percentage for t in self.trades]
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        return (avg_return / std_dev) if std_dev > 0 else 0.0


class PaperTrader:
    """
    Paper trading simulator with realistic execution

    Features:
    - Virtual balance management
    - Simulated fills with slippage
    - Trade history and analytics
    - Export results
    """

    def __init__(self, starting_balance: float = 100.0):
        self.account = PaperAccount(
            starting_balance=starting_balance,
            current_balance=starting_balance
        )
        self.trade_counter = 0

    def get_balance(self) -> float:
        """Get current balance"""
        return self.account.current_balance

    def get_available_balance(self) -> float:
        """Get available balance for trading"""
        return self.account.get_available_balance()

    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        game_id: Optional[str] = None,
        team: str = "",
        slippage: float = 0.001
    ) -> Optional[PaperPosition]:
        """
        Simulate placing an order

        Args:
            token_id: Market token ID
            side: "BUY" or "SELL"
            price: Limit price
            size: Size in USDC
            game_id: Game ID for tracking
            team: Team name for tracking
            slippage: Simulated slippage (default 0.1%)

        Returns: PaperPosition if successful
        """
        # Check balance
        available = self.get_available_balance()
        if available < size:
            logger.error(f"Insufficient balance: ${available:.2f} < ${size:.2f}")
            return None

        # Simulate fill with slippage
        if side.upper() == "BUY":
            fill_price = price * (1 + slippage)
        else:
            fill_price = price * (1 - slippage)

        fill_price = max(0.01, min(0.99, fill_price))

        # Create position
        position_id = f"paper_{int(time.time())}_{self.trade_counter}"
        self.trade_counter += 1

        position = PaperPosition(
            position_id=position_id,
            token_id=token_id,
            side=side.upper(),
            size=size,
            entry_price=fill_price,
            current_price=fill_price,
            entry_time=time.time(),
            game_id=game_id,
            team=team
        )

        self.account.positions[position_id] = position

        logger.info(f"📄 [PAPER] Order placed: {side} ${size:.2f} @ {fill_price:.3f}")
        logger.info(f"   Position ID: {position_id}")
        logger.info(f"   Available balance: ${self.get_available_balance():.2f}")

        return position

    def close_position(
        self,
        position_id: str,
        current_price: float,
        reason: str = "",
        slippage: float = 0.001
    ) -> bool:
        """
        Close a paper trading position

        Args:
            position_id: Position to close
            current_price: Current market price
            reason: Reason for closing
            slippage: Exit slippage

        Returns: True if successful
        """
        if position_id not in self.account.positions:
            logger.error(f"Position {position_id} not found")
            return False

        position = self.account.positions[position_id]

        # Simulate fill with slippage
        if position.side == "BUY":
            exit_price = current_price * (1 - slippage)
        else:
            exit_price = current_price * (1 + slippage)

        exit_price = max(0.01, min(0.99, exit_price))

        # Calculate P&L
        position.current_price = exit_price
        pnl = position.get_pnl()
        pnl_pct = position.get_pnl_percentage()

        # Update balance
        self.account.current_balance += pnl
        self.account.total_pnl += pnl

        # Record trade
        trade = PaperTrade(
            trade_id=position_id,
            token_id=position.token_id,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            size=position.size,
            pnl=pnl,
            pnl_percentage=pnl_pct,
            entry_time=position.entry_time,
            exit_time=time.time(),
            duration_seconds=time.time() - position.entry_time,
            exit_reason=reason,
            game_id=position.game_id,
            team=position.team
        )

        self.account.trades.append(trade)

        # Remove position
        del self.account.positions[position_id]

        symbol = "✅" if pnl > 0 else "❌"
        logger.info(f"📄 [PAPER] {symbol} Position closed: ${pnl:.2f} ({pnl_pct:.2f}%) - {reason}")
        logger.info(f"   Balance: ${self.account.current_balance:.2f} (PnL: ${self.account.total_pnl:.2f})")

        return True

    def update_position_prices(self, prices: Dict[str, float]):
        """
        Update current prices for all positions

        Args:
            prices: Dict of token_id -> current_price
        """
        for position in self.account.positions.values():
            if position.token_id in prices:
                position.current_price = prices[position.token_id]

    def get_active_positions(self) -> List[PaperPosition]:
        """Get all open positions"""
        return list(self.account.positions.values())

    def get_statistics(self) -> Dict:
        """Get comprehensive trading statistics"""
        account = self.account

        return {
            "starting_balance": account.starting_balance,
            "current_balance": account.current_balance,
            "total_pnl": account.total_pnl,
            "total_pnl_percentage": (account.total_pnl / account.starting_balance * 100) if account.starting_balance > 0 else 0,
            "total_trades": len(account.trades),
            "win_rate": account.get_win_rate(),
            "avg_win": account.get_avg_win(),
            "avg_loss": account.get_avg_loss(),
            "sharpe_ratio": account.get_sharpe_ratio(),
            "open_positions": len(account.positions),
            "total_exposure": account.get_total_exposure(),
            "available_balance": account.get_available_balance()
        }

    def display_statistics(self):
        """Display trading statistics"""
        stats = self.get_statistics()

        print("\n" + "=" * 60)
        print("📄 PAPER TRADING RESULTS")
        print("=" * 60)
        print(f"Starting Balance:     ${stats['starting_balance']:.2f}")
        print(f"Current Balance:      ${stats['current_balance']:.2f}")
        print(f"Total P&L:            ${stats['total_pnl']:.2f} ({stats['total_pnl_percentage']:.2f}%)")
        print("-" * 60)
        print(f"Total Trades:         {stats['total_trades']}")
        print(f"Win Rate:             {stats['win_rate']:.1f}%")
        print(f"Avg Win:              ${stats['avg_win']:.2f}")
        print(f"Avg Loss:             ${stats['avg_loss']:.2f}")
        print(f"Sharpe Ratio:         {stats['sharpe_ratio']:.2f}")
        print("-" * 60)
        print(f"Open Positions:       {stats['open_positions']}")
        print(f"Total Exposure:       ${stats['total_exposure']:.2f}")
        print(f"Available Balance:    ${stats['available_balance']:.2f}")
        print("=" * 60 + "\n")

    def export_results(self, filename: str = "paper_trading_results.json"):
        """Export trading results to JSON file"""
        stats = self.get_statistics()

        trades_data = [
            {
                "trade_id": t.trade_id,
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "size": t.size,
                "pnl": t.pnl,
                "pnl_percentage": t.pnl_percentage,
                "duration_seconds": t.duration_seconds,
                "exit_reason": t.exit_reason
            }
            for t in self.account.trades
        ]

        results = {
            "statistics": stats,
            "trades": trades_data
        }

        filepath = Path(filename)
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results exported to {filepath}")


if __name__ == "__main__":
    # Test paper trading
    logging.basicConfig(level=logging.INFO)

    print("\n=== Paper Trading Test ===\n")

    trader = PaperTrader(starting_balance=100.0)

    # Simulate some trades
    print("Starting balance: $100.00\n")

    # Trade 1: Win
    print("Trade 1: Buy $10 @ 0.50")
    pos1 = trader.place_order("token_1", "BUY", 0.50, 10.0, team="Lakers")
    if pos1:
        time.sleep(0.1)
        trader.close_position(pos1.position_id, 0.55, "Take Profit")

    # Trade 2: Loss
    print("\nTrade 2: Buy $10 @ 0.60")
    pos2 = trader.place_order("token_2", "BUY", 0.60, 10.0, team="Celtics")
    if pos2:
        time.sleep(0.1)
        trader.close_position(pos2.position_id, 0.57, "Stop Loss")

    # Trade 3: Win
    print("\nTrade 3: Buy $15 @ 0.45")
    pos3 = trader.place_order("token_3", "BUY", 0.45, 15.0, team="Warriors")
    if pos3:
        time.sleep(0.1)
        trader.close_position(pos3.position_id, 0.48, "Take Profit")

    # Display results
    trader.display_statistics()

    # Export
    trader.export_results("test_paper_results.json")
    print("✅ Results exported to test_paper_results.json")
