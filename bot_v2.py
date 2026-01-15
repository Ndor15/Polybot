"""
NBA Polymarket Trading Bot V2 - Improved Version

New Features:
- Real trading with py-clob-client OR paper trading mode
- Intelligent market matching with team name normalization
- Better signal confidence scoring
- Comprehensive analytics and export
- Faster execution

Usage:
    # Paper trading (safe testing)
    python bot_v2.py --paper

    # Real trading (requires POLYMARKET_PRIVATE_KEY)
    python bot_v2.py --live

Author: AI-Generated
Version: 2.0
"""
import logging
import time
import signal
import sys
import argparse
from typing import List, Optional
import colorlog

from config import config
from nba_client import NBAClient, NBAGame
from signal_analyzer import SignalAnalyzer, TradingSignal, SignalDirection
from risk_manager import RiskManager
from market_matcher import MarketMatcher

# Import trading clients
from paper_trader import PaperTrader
try:
    from polymarket_trader import PolymarketTrader
    REAL_TRADING_AVAILABLE = True
except ImportError:
    REAL_TRADING_AVAILABLE = False
    logging.warning("Real trading unavailable - py-clob-client not installed")


# Configure logging
def setup_logging():
    """Setup colored logging"""
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

    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    ))

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    logger.addHandler(handler)
    logger.addHandler(file_handler)


logger = logging.getLogger(__name__)


class NBAPolymarketBotV2:
    """Improved NBA Polymarket trading bot"""

    def __init__(self, paper_mode: bool = True, starting_balance: float = 100.0):
        self.paper_mode = paper_mode

        # Initialize components
        self.nba_client = NBAClient()
        self.signal_analyzer = SignalAnalyzer()
        self.risk_manager = RiskManager(max_total_exposure_usdc=starting_balance * 0.5)
        self.market_matcher = MarketMatcher()

        # Initialize trader (paper or real)
        if paper_mode:
            logger.info("🧪 Running in PAPER TRADING mode")
            self.trader = PaperTrader(starting_balance=starting_balance)
        else:
            if not REAL_TRADING_AVAILABLE:
                raise ImportError("Real trading requires py-clob-client. Install with: pip install py-clob-client")
            logger.info("💰 Running in LIVE TRADING mode")
            self.trader = PolymarketTrader()

        self.running = False
        self.iteration = 0

        # Markets cache
        self.markets_cache = []
        self.last_market_fetch = 0
        self.market_cache_ttl = 60  # Refresh markets every 60 seconds

        # Setup shutdown handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown gracefully"""
        logger.info("\n🛑 Shutdown signal received...")
        self.running = False

    def start(self):
        """Start the bot"""
        mode = "PAPER" if self.paper_mode else "LIVE"
        logger.info(f"🏀 NBA Polymarket Bot V2 Starting ({mode} mode)...")
        logger.info("=" * 60)

        if not self.paper_mode and not config.validate():
            logger.error("Configuration validation failed. Check .env file")
            return

        config.display()

        # Get initial balance
        try:
            balance = self.trader.get_balance()
            logger.info(f"💵 Starting balance: ${balance:.2f} USDC")
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return

        self.running = True
        logger.info("✅ Bot is now running. Press Ctrl+C to stop.\n")

        try:
            self._main_loop()
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self._shutdown()

    def _fetch_markets(self) -> List[dict]:
        """Fetch Polymarket NBA markets with caching"""
        current_time = time.time()

        # Use cache if still valid
        if self.markets_cache and (current_time - self.last_market_fetch) < self.market_cache_ttl:
            return self.markets_cache

        # Fetch fresh markets
        try:
            import requests
            response = requests.get(
                f"{config.POLYMARKET_GAMMA_API}/events",
                params={
                    "series_id": config.NBA_SERIES_ID,
                    "active": "true",
                    "closed": "false"
                },
                timeout=10
            )
            response.raise_for_status()
            events = response.json()

            # Extract markets
            markets = []
            for event in events:
                for market in event.get("markets", []):
                    # Add event info to market
                    market["event_title"] = event.get("title", "")
                    market["event_description"] = event.get("description", "")
                    markets.append(market)

            self.markets_cache = markets
            self.last_market_fetch = current_time

            logger.debug(f"Fetched {len(markets)} NBA markets")
            return markets

        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return self.markets_cache  # Return cached if fetch fails

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
                    time.sleep(config.UPDATE_INTERVAL_SECONDS * 3)
                    continue

                # 2. Fetch Polymarket markets
                markets = self._fetch_markets()
                logger.info(f"Found {len(markets)} active NBA markets")

                # 3. Update position prices
                if hasattr(self.trader, 'update_positions'):
                    self.trader.update_positions()

                # 4. Check exits (SL/TP/Time)
                self._check_exits(markets)

                # 5. Analyze games and generate signals
                all_signals = []
                for game in live_games:
                    signals = self.signal_analyzer.analyze_game(game)

                    # Match each signal to a market
                    for signal in signals:
                        market = self.market_matcher.match_game_to_market(game, markets)
                        if market:
                            signal.metadata["market"] = market
                            all_signals.append(signal)

                if all_signals:
                    logger.info(f"🎯 Generated {len(all_signals)} trading signals")
                    for sig in all_signals:
                        logger.info(f"   {sig}")

                # 6. Filter and execute best signal
                high_conf_signals = self.signal_analyzer.filter_signals(all_signals, min_confidence=0.65)

                if high_conf_signals:
                    best_signal = self.signal_analyzer.get_best_signal(high_conf_signals)
                    if best_signal:
                        self._execute_signal(best_signal)

                # 7. Display metrics every 10 iterations
                if self.iteration % 10 == 0:
                    self._display_status()

                # 8. Check if should pause
                positions = self.trader.get_active_positions()
                should_pause, reason = self.risk_manager.should_pause_trading(positions)
                if should_pause:
                    logger.warning(f"⚠️  Trading paused: {reason}")
                    time.sleep(60)
                    continue

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)

            # Wait before next iteration
            time.sleep(config.UPDATE_INTERVAL_SECONDS)

    def _check_exits(self, markets: List[dict]):
        """Check positions for exit conditions"""
        positions = self.trader.get_active_positions()

        if not positions:
            return

        # Build price map for paper trading
        if self.paper_mode:
            price_map = {}
            for market in markets:
                for outcome in market.get("outcomes", []):
                    token_id = outcome.get("token_id")
                    price = outcome.get("price", 0.5)
                    if token_id:
                        price_map[token_id] = price

            self.trader.update_position_prices(price_map)

        # Check each position
        to_close = []

        for position in positions:
            # Check stop loss
            if position.should_stop_loss():
                to_close.append((position, "Stop Loss"))

            # Check take profit
            elif position.should_take_profit():
                to_close.append((position, "Take Profit"))

            # Check expiry
            elif position.is_expired():
                to_close.append((position, "Position Expired"))

        # Close positions
        for position, reason in to_close:
            logger.info(f"🔔 Exit triggered: {position.position_id} - {reason}")

            if self.paper_mode:
                success = self.trader.close_position(
                    position.position_id,
                    position.current_price,
                    reason
                )
            else:
                success = self.trader.close_position(position.position_id, reason)

            if success:
                self.risk_manager.record_trade_result(position, reason)

    def _execute_signal(self, signal: TradingSignal):
        """Execute a trading signal"""
        logger.info(f"\n💡 Executing signal: {signal}")

        market = signal.metadata.get("market")
        if not market:
            logger.warning("No market found for signal")
            return

        # Check if can open position
        positions = self.trader.get_active_positions()
        balance = self.trader.get_balance() if hasattr(self.trader, 'get_balance') else 100.0

        can_open, reason = self.risk_manager.can_open_position(signal, positions, balance)

        if not can_open:
            logger.warning(f"Cannot open position: {reason}")
            return

        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(signal, balance)

        # Determine which outcome to bet on
        bet_on_team = "BUY" in signal.direction.value
        token_id = self.market_matcher.get_token_id_for_team(market, signal.team, bet_on_team)

        if not token_id:
            logger.warning(f"Could not find token ID for {signal.team}")
            return

        # Get current price
        price = None
        for outcome in market.get("outcomes", []):
            if outcome.get("token_id") == token_id:
                price = outcome.get("price", 0.5)
                break

        if price is None:
            logger.warning("Could not get market price")
            return

        # Determine side
        side = "BUY" if bet_on_team else "SELL"

        # Place order
        logger.info(f"📤 Placing order: {side} ${position_size:.2f} on {signal.team} @ {price:.3f}")

        if self.paper_mode:
            position = self.trader.place_order(
                token_id=token_id,
                side=side,
                price=price,
                size=position_size,
                game_id=signal.game_id,
                team=signal.team
            )
        else:
            position = self.trader.place_market_order(
                token_id=token_id,
                side=side,
                size=position_size,
                game_id=signal.game_id,
                team=signal.team
            )

        if position:
            logger.info(f"✅ Position opened successfully")
        else:
            logger.error(f"❌ Failed to open position")

    def _display_status(self):
        """Display current bot status"""
        positions = self.trader.get_active_positions()

        if self.paper_mode and hasattr(self.trader, 'display_statistics'):
            self.trader.display_statistics()
        else:
            self.risk_manager.display_metrics(positions)

    def _shutdown(self):
        """Graceful shutdown"""
        logger.info("\n🛑 Shutting down bot...")

        # Close all positions
        positions = self.trader.get_active_positions()

        if positions:
            logger.info(f"Closing {len(positions)} open positions...")

            for position in positions:
                if self.paper_mode:
                    self.trader.close_position(
                        position.position_id,
                        position.current_price,
                        "Bot shutdown"
                    )
                else:
                    self.trader.close_position(position.position_id, "Bot shutdown")

                self.risk_manager.record_trade_result(position, "Bot shutdown")

        # Display final stats
        logger.info("\n=== Final Results ===")
        self._display_status()

        # Export results if paper trading
        if self.paper_mode and hasattr(self.trader, 'export_results'):
            filename = f"paper_results_{int(time.time())}.json"
            self.trader.export_results(filename)
            logger.info(f"📊 Results exported to {filename}")

        logger.info("✅ Bot shutdown complete")


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description="NBA Polymarket Trading Bot V2")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run in LIVE trading mode (requires py-clob-client and POLYMARKET_PRIVATE_KEY)"
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        help="Run in PAPER trading mode (default, safe testing)"
    )
    parser.add_argument(
        "--balance",
        type=float,
        default=100.0,
        help="Starting balance for paper trading (default: 100 USDC)"
    )

    args = parser.parse_args()

    # Default to paper mode if neither specified
    paper_mode = True if (not args.live or args.paper) else False

    setup_logging()

    try:
        bot = NBAPolymarketBotV2(
            paper_mode=paper_mode,
            starting_balance=args.balance
        )
        bot.start()
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)


if __name__ == "__main__":
    main()
