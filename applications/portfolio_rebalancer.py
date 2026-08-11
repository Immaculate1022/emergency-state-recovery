"""
Self-Healing Financial Portfolio Rebalancer

Application of Emergency State Recovery to portfolio management.
Tracks topological peak (highest risk-adjusted return) and automatically
rebalances when strategy destabilizes.
"""

import sys
sys.path.insert(0, '/home/ubuntu/emergency-state-recovery')

from core.state_recovery import EmergencyStateRecovery, StateSnapshot
import numpy as np
import json
from datetime import datetime


class PortfolioRebalancer:
    """
    Self-healing portfolio manager using Emergency State Recovery.
    """
    
    def __init__(self, initial_allocation: dict, decay_constant: int = 500):
        """
        Initialize portfolio rebalancer.
        
        Args:
            initial_allocation: Dict of {asset: weight}
            decay_constant: Confidence decay time constant
        """
        self.allocation = initial_allocation.copy()
        self.recovery = EmergencyStateRecovery(decay_constant=decay_constant, instability_threshold=0.15)
        self.price_history = {}
        self.returns_history = []
        
        # Record initial state
        self._record_current_state("initial_allocation")
    
    def _calculate_portfolio_return(self, returns: dict) -> float:
        """Calculate weighted portfolio return."""
        total_return = 0.0
        for asset, weight in self.allocation.items():
            total_return += weight * returns.get(asset, 0.0)
        return total_return
    
    def _calculate_sharpe_ratio(self, returns_list: list, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio for risk-adjusted return."""
        if len(returns_list) < 2:
            return 0.0
        
        returns_array = np.array(returns_list)
        excess_returns = returns_array - risk_free_rate / 252  # Daily risk-free rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    
    def _record_current_state(self, state_label: str):
        """Record current portfolio state."""
        state_id = f"portfolio_{state_label}_{len(self.recovery.states)}"
        
        # Use Sharpe ratio as performance metric
        sharpe = self._calculate_sharpe_ratio(self.returns_history)
        
        state_vector = {
            'allocation': self.allocation.copy(),
            'sharpe_ratio': sharpe,
            'total_return': sum(self.returns_history) if self.returns_history else 0.0,
            'num_periods': len(self.returns_history)
        }
        
        self.recovery.record_state(
            state_id=state_id,
            performance_metric=sharpe,
            state_vector=state_vector,
            metadata={'label': state_label}
        )
    
    def update_prices(self, asset_returns: dict):
        """
        Update portfolio with new period returns.
        
        Args:
            asset_returns: Dict of {asset: return_rate}
        """
        # Calculate portfolio return
        portfolio_return = self._calculate_portfolio_return(asset_returns)
        self.returns_history.append(portfolio_return)
        
        # Check stability
        is_stable = self.recovery.check_stability(self._calculate_sharpe_ratio(self.returns_history))
        
        if not is_stable and len(self.returns_history) > 10:
            print(f"\n⚠️  Portfolio instability detected!")
            self._trigger_rebalance()
        else:
            # Record state periodically
            if len(self.returns_history) % 20 == 0:
                self._record_current_state(f"period_{len(self.returns_history)}")
    
    def _trigger_rebalance(self):
        """Trigger emergency rebalance to known good state."""
        current_sharpe = self._calculate_sharpe_ratio(self.returns_history)
        
        # Trigger recovery
        target_state = self.recovery.trigger_recall(
            reason="Portfolio performance degradation",
            diagnostics={
                'current_sharpe': current_sharpe,
                'threshold': self.recovery.instability_threshold
            }
        )
        
        if target_state:
            # Restore allocation
            self.allocation = target_state.state_vector['allocation'].copy()
            print(f"✓ Portfolio rebalanced to state: {target_state.state_id}")
            print(f"  Restored Sharpe ratio: {target_state.state_vector['sharpe_ratio']:.4f}")
    
    def get_status(self) -> dict:
        """Get current portfolio status."""
        current_sharpe = self._calculate_sharpe_ratio(self.returns_history)
        
        return {
            'current_allocation': self.allocation,
            'current_sharpe_ratio': current_sharpe,
            'total_return': sum(self.returns_history),
            'periods_tracked': len(self.returns_history),
            'total_rebalances': len(self.recovery.recall_history),
            'best_state_sharpe': self.recovery.states[self.recovery.best_state_id].performance_metric 
                                 if self.recovery.best_state_id else None
        }


class PortfolioSimulation:
    """Simulate portfolio performance with market regimes."""
    
    def __init__(self, rebalancer: PortfolioRebalancer, num_periods: int = 500):
        self.rebalancer = rebalancer
        self.num_periods = num_periods
    
    def run_with_regime_shifts(self):
        """Run simulation with market regime shifts."""
        print("Starting portfolio simulation with regime shifts...")
        
        for period in range(self.num_periods):
            # Simulate different market regimes
            if period < 100:
                # Bull market
                returns = {
                    'stocks': np.random.normal(0.0008, 0.01),
                    'bonds': np.random.normal(0.0002, 0.003),
                    'commodities': np.random.normal(0.0001, 0.015)
                }
            elif period < 200:
                # Volatility spike
                returns = {
                    'stocks': np.random.normal(-0.001, 0.025),
                    'bonds': np.random.normal(0.0005, 0.008),
                    'commodities': np.random.normal(0.0, 0.03)
                }
            elif period < 350:
                # Recovery
                returns = {
                    'stocks': np.random.normal(0.0005, 0.012),
                    'bonds': np.random.normal(0.0003, 0.004),
                    'commodities': np.random.normal(0.0002, 0.012)
                }
            else:
                # Crash
                returns = {
                    'stocks': np.random.normal(-0.002, 0.035),
                    'bonds': np.random.normal(0.001, 0.006),
                    'commodities': np.random.normal(-0.0005, 0.04)
                }
            
            self.rebalancer.update_prices(returns)
            
            if (period + 1) % 50 == 0:
                status = self.rebalancer.get_status()
                print(f"\nPeriod {period + 1}:")
                print(f"  Sharpe Ratio: {status['current_sharpe_ratio']:.4f}")
                print(f"  Total Return: {status['total_return']:.4f}")
                print(f"  Rebalances: {status['total_rebalances']}")
        
        return self.rebalancer.get_status()


if __name__ == "__main__":
    # Initialize portfolio with 60/30/10 allocation
    initial_allocation = {
        'stocks': 0.60,
        'bonds': 0.30,
        'commodities': 0.10
    }
    
    rebalancer = PortfolioRebalancer(initial_allocation, decay_constant=500)
    simulation = PortfolioSimulation(rebalancer, num_periods=500)
    
    # Run simulation
    final_status = simulation.run_with_regime_shifts()
    
    # Print final report
    print("\n" + "="*60)
    print("PORTFOLIO RECOVERY SIMULATION COMPLETE")
    print("="*60)
    print(f"Final Sharpe Ratio: {final_status['current_sharpe_ratio']:.4f}")
    print(f"Total Return: {final_status['total_return']:.4f}")
    print(f"Total Rebalances Triggered: {final_status['total_rebalances']}")
    print(f"Best State Sharpe Ratio: {final_status['best_state_sharpe']:.4f}")
    
    # Export diagnostics
    diag = rebalancer.recovery.get_diagnostics()
    print(f"\nTotal States Recorded: {diag['total_states_recorded']}")
    print(f"Confidence Decay Constant: {diag['decay_constant']}")
