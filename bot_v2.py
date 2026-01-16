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
from nba_official_client import NBAOfficialClient
from signal_analyzer import SignalAnalyzer, TradingSignal, SignalDirection
from player_prop_analyzer import PlayerPropAnalyzer, PlayerPropSignal
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
    """Setup colored logging (Windows compatible)"""
    # Configure console handler with UTF-8 on Windows
    import sys
    if sys.platform == 'win32':
        # Try to enable UTF-8 mode on Windows
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except:
            pass

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

    file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
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
        # Use NBA Official API (more permissive, no rate limits)
        self.nba_client = NBAOfficialClient()  # Primary client for live games
        self.signal_analyzer = SignalAnalyzer()
        self.player_prop_analyzer = PlayerPropAnalyzer(config)  # For player prop analysis
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

        # Test trade mode flag
        self.test_trade_completed = False

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

                # 5. Analyze games and generate signals (GAME-LEVEL + PLAYER PROPS)
                all_signals = []
                all_player_prop_signals = []

                for game in live_games:
                    logger.info(f"Analyzing: {game.away_team} @ {game.home_team} (Score: {game.away_score}-{game.home_score}, Period: {game.period})")

                    # 5a. Game-level signals (momentum, lead changes, etc.)
                    signals = self.signal_analyzer.analyze_game(game)
                    logger.info(f"  Generated {len(signals)} game-level signals")

                    # Match each signal to a market
                    for signal in signals:
                        market = self.market_matcher.match_game_to_market(game, markets)
                        if market:
                            logger.debug(f"  Matched signal to market: {market.get('event_title', 'N/A')}")
                            signal.metadata["market"] = market
                            all_signals.append(signal)
                        else:
                            logger.warning(f"  No market found for signal: {signal}")

                    # 5b. Player prop signals (points, assists, rebounds, etc.)
                    try:
                        prop_signals = self._analyze_player_props(game, markets)
                        logger.info(f"  Generated {len(prop_signals)} player prop signals")
                        all_player_prop_signals.extend(prop_signals)
                    except Exception as e:
                        logger.error(f"  Error analyzing player props: {e}", exc_info=True)

                # 6. Combine and display all signals
                total_signals = len(all_signals) + len(all_player_prop_signals)

                if all_signals:
                    logger.info(f"🎯 Game-level signals: {len(all_signals)}")
                    for sig in all_signals:
                        logger.info(f"   {sig}")

                if all_player_prop_signals:
                    logger.info(f"🏃 Player prop signals: {len(all_player_prop_signals)}")
                    for sig in all_player_prop_signals[:5]:  # Show top 5
                        logger.info(f"   {sig.player_name}: {sig.stat_type} {sig.side.upper()} {sig.market_line} (conf: {sig.confidence:.2f})")

                if total_signals == 0:
                    logger.info("No signals generated")

                # 7. Filter and execute best signal (game-level)
                high_conf_signals = self.signal_analyzer.filter_signals(all_signals, min_confidence=0.30)
                logger.info(f"Game signals after confidence filter (>0.30): {len(high_conf_signals)}")

                # Filter player prop signals
                high_conf_prop_signals = [s for s in all_player_prop_signals if s.confidence >= 0.20]
                logger.info(f"Player prop signals after confidence filter (>0.20): {len(high_conf_prop_signals)}")

                # Execute best signal (prioritize higher confidence)
                best_game_signal = self.signal_analyzer.get_best_signal(high_conf_signals) if high_conf_signals else None
                best_prop_signal = max(high_conf_prop_signals, key=lambda s: s.confidence) if high_conf_prop_signals else None

                # Choose the signal with highest confidence
                if best_game_signal and best_prop_signal:
                    if best_prop_signal.confidence > best_game_signal.confidence:
                        logger.info(f"📊 Executing best PLAYER PROP signal: {best_prop_signal.player_name} {best_prop_signal.stat_type} {best_prop_signal.side}")
                        self._execute_player_prop_signal(best_prop_signal)
                    else:
                        logger.info(f"⚽ Executing best GAME signal: {best_game_signal}")
                        self._execute_signal(best_game_signal)
                elif best_prop_signal:
                    logger.info(f"📊 Executing best PLAYER PROP signal: {best_prop_signal.player_name} {best_prop_signal.stat_type} {best_prop_signal.side}")
                    self._execute_player_prop_signal(best_prop_signal)
                elif best_game_signal:
                    logger.info(f"⚽ Executing best GAME signal: {best_game_signal}")
                    self._execute_signal(best_game_signal)
                else:
                    logger.info("No high-confidence signals to execute")

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

        # Override for test mode
        if config.TEST_TRADE_MODE:
            position_size = 1.0
            logger.info("🧪 TEST MODE: Forcing position size to $1.00")

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

            # Stop bot after test trade
            if config.TEST_TRADE_MODE and not self.test_trade_completed:
                self.test_trade_completed = True
                logger.info("🧪 TEST TRADE COMPLETED! Stopping bot...")
                logger.info(f"📊 Test trade: {side} ${position_size:.2f} on {signal.team}")
                self.running = False

        else:
            logger.error(f"❌ Failed to open position")

    def _analyze_player_props(self, game: NBAGame, markets: List[dict]) -> List[PlayerPropSignal]:
        """
        Analyze player props for a game

        Args:
            game: NBAGame object
            markets: List of available Polymarket markets

        Returns: List of PlayerPropSignal objects
        """
        all_prop_signals = []

        try:
            # Fetch detailed player box scores
            box_scores = self.nba_client.get_player_box_scores(game.game_id)

            home_players = box_scores.get('home_players', [])
            away_players = box_scores.get('away_players', [])
            all_players = home_players + away_players

            if not all_players:
                logger.debug(f"No player box scores available for game {game.game_id}")
                return []

            # Calculate score differential
            score_diff = game.home_score - game.away_score

            # For each player, find their prop markets and analyze
            for player in all_players:
                player_name = player.get('name', '')
                if not player_name:
                    continue

                # Parse minutes
                minutes_str = player.get('minutes', 'PT00M00.00S')
                minutes_played = self._parse_minutes(minutes_str)

                # Skip players with little playing time
                if minutes_played < 5.0:
                    continue

                # Add pacing data to player stats
                player['pacing'] = self.nba_client.get_player_pacing(
                    player,
                    minutes_played,
                    game.period
                )

                # Also add game_id for signal tracking
                player['game_id'] = game.game_id

                # Find all prop markets for this player
                player_markets = self.market_matcher.find_player_prop_markets(
                    game,
                    player_name,
                    markets
                )

                if not player_markets:
                    continue

                # Analyze each prop
                signals = self.player_prop_analyzer.analyze_player_props(
                    player_stats=player,
                    period=game.period,
                    score_differential=score_diff,
                    player_markets=player_markets
                )

                # Add market info to signals
                for signal in signals:
                    # Find the matching market
                    matching_market = None
                    for market in player_markets:
                        question = market.get('question', '').lower()
                        if signal.stat_type in question and str(signal.market_line) in question:
                            matching_market = market
                            break

                    if matching_market:
                        signal.metadata = {'market': matching_market}
                        all_prop_signals.append(signal)

        except Exception as e:
            logger.error(f"Error in _analyze_player_props: {e}", exc_info=True)

        return all_prop_signals

    def _execute_player_prop_signal(self, signal: PlayerPropSignal):
        """Execute a player prop signal"""
        logger.info(f"\n📊 Executing player prop: {signal.player_name} - {signal.stat_type} {signal.side.upper()} {signal.market_line}")
        logger.info(f"   Current: {signal.current_value} | Projected: {signal.projected_value}")
        logger.info(f"   Reason: {signal.reason}")

        market = signal.metadata.get("market") if hasattr(signal, 'metadata') else None
        if not market:
            logger.warning("No market found for player prop signal")
            return

        # Check if can open position
        positions = self.trader.get_active_positions()
        balance = self.trader.get_balance() if hasattr(self.trader, 'get_balance') else 100.0

        # Create a fake TradingSignal for risk manager compatibility
        fake_signal = TradingSignal(
            game_id=signal.game_id,
            team=signal.player_name,
            direction=SignalDirection.BUY if signal.side == 'over' else SignalDirection.SELL,
            confidence=signal.confidence,
            reason=signal.reason,
            strategy=f"PlayerProp_{signal.stat_type}",
            metadata={}
        )

        can_open, reason = self.risk_manager.can_open_position(fake_signal, positions, balance)

        if not can_open:
            logger.warning(f"Cannot open position: {reason}")
            return

        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(fake_signal, balance)

        # Get token ID for the prop side
        token_id = self.market_matcher.get_token_id_for_prop_outcome(market, signal.side)

        if not token_id:
            logger.warning(f"Could not find token ID for {signal.side}")
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

        # Determine side (BUY for over, BUY for under means buying 'under' outcome)
        side = "BUY"  # Always buy the outcome we chose

        # Place order
        logger.info(f"📤 Placing order: {side} ${position_size:.2f} on {signal.player_name} {signal.stat_type} {signal.side.upper()} @ {price:.3f}")

        if self.paper_mode:
            position = self.trader.place_order(
                token_id=token_id,
                side=side,
                price=price,
                size=position_size,
                game_id=signal.game_id,
                team=f"{signal.player_name} {signal.stat_type} {signal.side}"
            )
        else:
            position = self.trader.place_market_order(
                token_id=token_id,
                side=side,
                size=position_size,
                game_id=signal.game_id,
                team=f"{signal.player_name} {signal.stat_type} {signal.side}"
            )

        if position:
            logger.info(f"✅ Player prop position opened successfully")
        else:
            logger.error(f"❌ Failed to open player prop position")

    def _parse_minutes(self, minutes_str: str) -> float:
        """Parse ISO 8601 duration to minutes"""
        if not minutes_str or not isinstance(minutes_str, str):
            return 0.0

        try:
            import re
            match = re.search(r'PT(\d+)M(\d+(?:\.\d+)?)S', minutes_str)
            if match:
                mins = int(match.group(1))
                secs = float(match.group(2))
                return mins + secs / 60.0
        except:
            pass

        return 0.0

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
