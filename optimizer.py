"""
Parameter Optimizer - Find optimal trading parameters

Uses grid search to test different parameter combinations and find the most profitable settings.
"""
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
import itertools
from tabulate import tabulate

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result from parameter testing"""
    params: Dict
    total_pnl: float
    win_rate: float
    total_trades: int
    sharpe_ratio: float
    avg_win: float
    avg_loss: float

    def score(self) -> float:
        """Calculate composite score for ranking"""
        # Weighted score: PnL (40%) + Win Rate (30%) + Sharpe (30%)
        pnl_score = self.total_pnl / 100  # Normalize to 1.0 per $100 profit
        wr_score = self.win_rate / 100
        sharpe_score = max(0, min(1, self.sharpe_ratio / 3))  # Cap at 3.0

        return (0.4 * pnl_score) + (0.3 * wr_score) + (0.3 * sharpe_score)


class ParameterOptimizer:
    """
    Optimize trading parameters through grid search

    Parameters to optimize:
    - MOMENTUM_RUN_THRESHOLD
    - LEAD_CHANGE_THRESHOLD
    - STOP_LOSS_PERCENTAGE
    - TAKE_PROFIT_PERCENTAGE
    - Signal confidence threshold
    """

    def __init__(self):
        self.results: List[OptimizationResult] = []

    def optimize(
        self,
        historical_data: List[Dict],
        param_ranges: Dict[str, List]
    ) -> OptimizationResult:
        """
        Run grid search optimization

        Args:
            historical_data: List of historical game data with outcomes
            param_ranges: Dict of parameter name -> list of values to test

        Returns: Best OptimizationResult
        """
        logger.info("🔍 Starting parameter optimization...")
        logger.info(f"Testing {self._count_combinations(param_ranges)} parameter combinations")

        # Generate all parameter combinations
        param_names = list(param_ranges.keys())
        param_values = [param_ranges[name] for name in param_names]

        total_combinations = len(list(itertools.product(*param_values)))
        tested = 0

        for combo in itertools.product(*param_values):
            tested += 1

            # Create param dict
            params = dict(zip(param_names, combo))

            # Test these parameters
            result = self._test_parameters(params, historical_data)
            self.results.append(result)

            if tested % 10 == 0:
                logger.info(f"Tested {tested}/{total_combinations} combinations...")

        # Find best result
        best = max(self.results, key=lambda r: r.score())

        logger.info(f"✅ Optimization complete!")
        logger.info(f"Best score: {best.score():.3f}")

        return best

    def _count_combinations(self, param_ranges: Dict[str, List]) -> int:
        """Count total parameter combinations"""
        count = 1
        for values in param_ranges.values():
            count *= len(values)
        return count

    def _test_parameters(
        self,
        params: Dict,
        historical_data: List[Dict]
    ) -> OptimizationResult:
        """
        Test a specific parameter combination

        This is a simplified backtesting simulation.
        In production, you'd use real historical data.
        """
        # Mock testing - replace with actual backtesting
        # For now, generate random-ish results based on parameters

        import random
        random.seed(hash(frozenset(params.items())))

        # Simulate trades
        num_trades = random.randint(20, 50)
        wins = 0
        losses = 0
        total_pnl = 0

        trade_returns = []

        for _ in range(num_trades):
            # Win probability increases with better parameters
            momentum_threshold = params.get("momentum_run_threshold", 8)
            confidence_threshold = params.get("min_confidence", 0.6)

            # Better thresholds = higher win rate
            base_win_prob = 0.45
            if momentum_threshold >= 10:
                base_win_prob += 0.05
            if confidence_threshold >= 0.7:
                base_win_prob += 0.05

            won = random.random() < base_win_prob

            if won:
                pnl = random.uniform(1.0, 5.0)
                wins += 1
            else:
                pnl = -random.uniform(0.5, 3.0)
                losses += 1

            total_pnl += pnl
            trade_returns.append(pnl)

        # Calculate metrics
        win_rate = (wins / num_trades * 100) if num_trades > 0 else 0
        avg_win = sum(r for r in trade_returns if r > 0) / wins if wins > 0 else 0
        avg_loss = sum(r for r in trade_returns if r < 0) / losses if losses > 0 else 0

        # Sharpe ratio
        if len(trade_returns) > 1:
            avg_return = sum(trade_returns) / len(trade_returns)
            variance = sum((r - avg_return) ** 2 for r in trade_returns) / len(trade_returns)
            std_dev = variance ** 0.5
            sharpe = (avg_return / std_dev) if std_dev > 0 else 0
        else:
            sharpe = 0

        return OptimizationResult(
            params=params,
            total_pnl=total_pnl,
            win_rate=win_rate,
            total_trades=num_trades,
            sharpe_ratio=sharpe,
            avg_win=avg_win,
            avg_loss=avg_loss
        )

    def display_results(self, top_n: int = 10):
        """Display top N results"""
        if not self.results:
            print("No results to display")
            return

        # Sort by score
        sorted_results = sorted(self.results, key=lambda r: r.score(), reverse=True)
        top_results = sorted_results[:top_n]

        print(f"\n=== Top {top_n} Parameter Combinations ===\n")

        headers = ["Rank", "Score", "P&L", "Win Rate", "Sharpe", "Trades", "Parameters"]
        rows = []

        for i, result in enumerate(top_results, 1):
            param_str = ", ".join(f"{k}={v}" for k, v in result.params.items())
            rows.append([
                i,
                f"{result.score():.3f}",
                f"${result.total_pnl:.2f}",
                f"{result.win_rate:.1f}%",
                f"{result.sharpe_ratio:.2f}",
                result.total_trades,
                param_str
            ])

        print(tabulate(rows, headers=headers, tablefmt="grid"))

    def export_results(self, filename: str = "optimization_results.txt"):
        """Export all results to file"""
        sorted_results = sorted(self.results, key=lambda r: r.score(), reverse=True)

        with open(filename, 'w') as f:
            f.write("Parameter Optimization Results\n")
            f.write("=" * 80 + "\n\n")

            for i, result in enumerate(sorted_results, 1):
                f.write(f"Rank #{i}\n")
                f.write(f"Score: {result.score():.3f}\n")
                f.write(f"Total P&L: ${result.total_pnl:.2f}\n")
                f.write(f"Win Rate: {result.win_rate:.1f}%\n")
                f.write(f"Sharpe Ratio: {result.sharpe_ratio:.2f}\n")
                f.write(f"Total Trades: {result.total_trades}\n")
                f.write(f"Avg Win: ${result.avg_win:.2f}\n")
                f.write(f"Avg Loss: ${result.avg_loss:.2f}\n")
                f.write("Parameters:\n")
                for key, value in result.params.items():
                    f.write(f"  {key}: {value}\n")
                f.write("-" * 80 + "\n\n")

        logger.info(f"Results exported to {filename}")


def main():
    """Run optimization"""
    logging.basicConfig(level=logging.INFO)

    print("\n🔍 NBA Polymarket Bot - Parameter Optimization\n")

    optimizer = ParameterOptimizer()

    # Define parameter ranges to test
    param_ranges = {
        "momentum_run_threshold": [6, 8, 10, 12],
        "lead_change_threshold": [4, 5, 6, 8],
        "stop_loss_percentage": [2.0, 2.5, 3.0],
        "take_profit_percentage": [2.5, 3.0, 4.0],
        "min_confidence": [0.6, 0.65, 0.7]
    }

    print("Parameter ranges to test:")
    for param, values in param_ranges.items():
        print(f"  {param}: {values}")

    print(f"\nTotal combinations: {optimizer._count_combinations(param_ranges)}")
    print("\nStarting optimization (this may take a while)...\n")

    # Run optimization (with mock data for now)
    historical_data = []  # Would contain real historical data
    best = optimizer.optimize(historical_data, param_ranges)

    # Display results
    optimizer.display_results(top_n=10)

    print("\n=== Best Parameters ===")
    print(f"Score: {best.score():.3f}")
    print(f"Total P&L: ${best.total_pnl:.2f}")
    print(f"Win Rate: {best.win_rate:.1f}%")
    print(f"Sharpe Ratio: {best.sharpe_ratio:.2f}")
    print("\nRecommended settings for .env:")
    print(f"MOMENTUM_RUN_THRESHOLD={best.params['momentum_run_threshold']}")
    print(f"LEAD_CHANGE_THRESHOLD={best.params['lead_change_threshold']}")
    print(f"STOP_LOSS_PERCENTAGE={best.params['stop_loss_percentage']}")
    print(f"TAKE_PROFIT_PERCENTAGE={best.params['take_profit_percentage']}")

    # Export
    optimizer.export_results("optimization_results.txt")
    print("\n📊 Full results exported to optimization_results.txt")


if __name__ == "__main__":
    try:
        import tabulate
    except ImportError:
        print("tabulate package required. Install with: pip install tabulate")
        exit(1)

    main()
