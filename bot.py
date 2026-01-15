"""
NBA Polymarket Trading Bot - Main Entry Point

This bot trades on Polymarket NBA markets by:
1. Monitoring live NBA games in real-time
2. Detecting trading signals (momentum runs, lead changes, etc.)
3. Executing trades with automatic stop loss and take profit
4. Managing risk and position sizing

Trading Strategy:
- Fade momentum runs (bet against teams on big runs)
- Fade lead changes (contrarian approach)
- Exploit close game volatility
- React faster than the market

Author: AI-Generated
Version: 1.0
"""
import logging
import time
import signal
import sys
from typing import List
import colorlog

from config import config
from nba_client import NBAClient
from polymarket_client import PolymarketClient, Market
from signal_analyzer import SignalAnalyzer, TradingSignal, SignalDirection
from risk_manager import RiskManager


# Configure colored logging
def setup_logging():
    """Setup colored logging to console and file"""
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))

    # File handler
    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    ))

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    logger.addHandler(handler)
    logger.addHandler(file_handler)


logger = logging.getLogger(__name__)


class NBAPolymarketBot:
    """Main trading bot orchestrator"""

    def __init__(self):
        self.nba_client = NBAClient()
        self.polymarket_client = PolymarketClient()
        self.signal_analyzer = SignalAnalyzer()
        self.risk_manager = RiskManager(max_total_exposure_usdc=50.0)

        self.running = False
        self.iteration = 0

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("\n🛑 Shutdown signal received. Closing all positions...")
        self.running = False

    def start(self):
        """Start the trading bot"""
        logger.info("🏀 NBA Polymarket Trading Bot Starting...")
        logger.info("=" * 60)

        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed. Please check .env file")
            return

        config.display()

        self.running = True
        logger.info("✅ Bot is now running. Press Ctrl+C to stop.\n")

        try:
            self._main_loop()
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self._shutdown()

    def _main_loop(self):
        """Main trading loop"""
        while self.running:
            self.iteration += 1

            try:
                logger.info(f"--- Iteration {self.iteration} ---")

                # 1. Fetch live NBA games
                live_games = self.nba_client.get_live_games()
                logger.info(f"Found {len(live_games)} live NBA games")

                if not live_games:
                    logger.info("No live games. Waiting...")
                    time.sleep(config.UPDATE_INTERVAL_SECONDS * 2)
                    continue

                # 2. Fetch Polymarket NBA markets
                markets = self.polymarket_client.get_nba_markets()
                logger.info(f"Found {len(markets)} active NBA markets")

                # 3. Update positions with current prices
                self.polymarket_client.update_positions(markets)

                # 4. Check for exits (Stop Loss / Take Profit / Time)
                self._check_exits()

                # 5. Analyze games for signals
                all_signals = []
                for game in live_games:
                    signals = self.signal_analyzer.analyze_game(game)
                    all_signals.extend(signals)

                if all_signals:
                    logger.info(f"🎯 Generated {len(all_signals)} trading signals")
                    for sig in all_signals:
                        logger.info(f"   {sig}")

                # 6. Filter signals by confidence
                high_confidence_signals = self.signal_analyzer.filter_signals(
                    all_signals,
                    min_confidence=0.6
                )

                # 7. Execute trades on best signals
                if high_confidence_signals:
                    best_signal = self.signal_analyzer.get_best_signal(high_confidence_signals)
                    if best_signal:
                        self._execute_signal(best_signal, markets)

                # 8. Display metrics
                positions = self.polymarket_client.get_active_positions()
                if positions:
                    self.risk_manager.display_metrics(positions)

                # 9. Check if trading should be paused
                should_pause, reason = self.risk_manager.should_pause_trading(positions)
                if should_pause:
                    logger.warning(f"⚠️  Trading paused: {reason}")
                    time.sleep(60)  # Wait 1 minute
                    continue

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)

            # Wait before next iteration
            time.sleep(config.UPDATE_INTERVAL_SECONDS)

    def _check_exits(self):
        """Check all positions for exit conditions"""
        positions = self.polymarket_client.get_active_positions()

        if not positions:
            return

        to_close = self.polymarket_client.check_exits()

        for position, reason in to_close:
            logger.info(f"🔔 Exit condition triggered for {position.position_id}: {reason}")

            # Close the position
            success = self.polymarket_client.close_position(position.position_id, reason)

            if success:
                # Record trade result
                self.risk_manager.record_trade_result(position, reason)

    def _execute_signal(self, signal: TradingSignal, markets: List[Market]):
        """Execute a trading signal"""
        logger.info(f"\n💡 Processing signal: {signal}")

        # Get current positions
        positions = self.polymarket_client.get_active_positions()

        # Check if we can open a position
        can_open, reason = self.risk_manager.can_open_position(
            signal,
            positions,
            available_balance=100.0  # TODO: Get actual balance
        )

        if not can_open:
            logger.warning(f"Cannot open position: {reason}")
            return

        # Find the market for this game
        market = self.polymarket_client.find_market_for_game(signal.game_id, markets)

        if not market:
            logger.warning(f"No market found for game {signal.game_id}")
            return

        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(signal, available_balance=100.0)

        # Determine which outcome to bet on
        outcome_name = self._signal_to_outcome(signal, market)

        if not outcome_name:
            logger.warning("Could not determine outcome to bet on")
            return

        # Determine order side
        side = "BUY" if "BUY" in signal.direction.value else "SELL"

        # Place the order
        logger.info(f"📤 Placing order: {side} ${position_size:.2f} on {outcome_name}")

        position = self.polymarket_client.place_order(
            market=market,
            outcome_name=outcome_name,
            side=side,
            size=position_size,
            game_id=signal.game_id,
            team=signal.team
        )

        if position:
            logger.info(f"✅ Position opened successfully!")
            logger.info(f"   Entry Price: {position.entry_price:.3f}")
            logger.info(f"   Stop Loss: {config.STOP_LOSS_PERCENTAGE}%")
            logger.info(f"   Take Profit: {config.TAKE_PROFIT_PERCENTAGE}%")
        else:
            logger.error("❌ Failed to open position")

    def _signal_to_outcome(self, signal: TradingSignal, market: Market) -> str:
        """Convert a trading signal to a market outcome name"""
        # This is simplified - in production you'd need better logic
        # to match signals to actual market outcomes

        if "HOME" in signal.direction.value:
            # Betting on home team
            # Look for outcome matching home team
            if market.home_team:
                return market.home_team
            else:
                return "Yes"  # Default for simple Yes/No markets

        elif "AWAY" in signal.direction.value:
            # Betting on away team
            if market.away_team:
                return market.away_team
            else:
                return "No"

        return "Yes"  # Default fallback

    def _shutdown(self):
        """Graceful shutdown"""
        logger.info("\n🛑 Shutting down bot...")

        # Close all open positions
        positions = self.polymarket_client.get_active_positions()

        if positions:
            logger.info(f"Closing {len(positions)} open positions...")
            for position in positions:
                self.polymarket_client.close_position(
                    position.position_id,
                    reason="Bot shutdown"
                )
                self.risk_manager.record_trade_result(position, "Bot shutdown")

        # Display final statistics
        logger.info("\n=== Final Performance ===")
        self.risk_manager.display_metrics([])

        logger.info("✅ Bot shutdown complete.")


def main():
    """Entry point"""
    setup_logging()

    bot = NBAPolymarketBot()
    bot.start()


if __name__ == "__main__":
    main()
