"""
Reinforcement Learning Policy Recovery

Application of Emergency State Recovery to RL agents.
Prevents policy collapse by rolling back to best-performing policy checkpoints.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.state_recovery import EmergencyStateRecovery
import numpy as np
import json


class RLPolicyRecovery:
    """
    RL agent with automatic policy recovery.
    """
    
    def __init__(self, policy_dim: int = 10, decay_constant: int = 500):
        """
        Initialize RL agent with recovery.
        
        Args:
            policy_dim: Dimensionality of policy vector
            decay_constant: Confidence decay time constant
        """
        self.policy = np.random.randn(policy_dim) * 0.1
        self.policy_dim = policy_dim
        self.recovery = EmergencyStateRecovery(decay_constant=decay_constant, instability_threshold=0.2)
        self.episode_rewards = []
        self.episode_count = 0
        
        # Record initial policy
        self._record_policy_checkpoint("initial_policy")
    
    def _record_policy_checkpoint(self, label: str):
        """Record current policy as checkpoint."""
        state_id = f"policy_{label}_{self.episode_count}"
        
        # Use average reward as performance metric
        avg_reward = np.mean(self.episode_rewards[-100:]) if self.episode_rewards else 0.0
        
        state_vector = {
            'policy': self.policy.copy().tolist(),
            'avg_reward': avg_reward,
            'episode': self.episode_count
        }
        
        self.recovery.record_state(
            state_id=state_id,
            performance_metric=avg_reward,
            state_vector=state_vector,
            metadata={'label': label}
        )
    
    def run_episode(self, env_noise: float = 0.1) -> float:
        """
        Run one episode and return reward.
        
        Args:
            env_noise: Environmental noise level
            
        Returns:
            Episode reward
        """
        # Simulate episode: reward based on policy + noise
        action = np.dot(self.policy, np.random.randn(self.policy_dim))
        reward = action + np.random.randn() * env_noise
        
        self.episode_rewards.append(reward)
        self.episode_count += 1
        
        # Check stability every 10 episodes
        if self.episode_count % 10 == 0:
            avg_reward = np.mean(self.episode_rewards[-100:])
            is_stable = self.recovery.check_stability(avg_reward)
            
            if not is_stable:
                self._trigger_policy_recovery()
            else:
                self._record_policy_checkpoint(f"episode_{self.episode_count}")
        
        return reward
    
    def _trigger_policy_recovery(self):
        """Trigger policy rollback to best checkpoint."""
        current_avg = np.mean(self.episode_rewards[-100:]) if self.episode_rewards else 0.0
        
        target_state = self.recovery.trigger_recall(
            reason="Policy performance degradation",
            diagnostics={
                'current_avg_reward': current_avg,
                'episode': self.episode_count
            }
        )
        
        if target_state:
            # Restore policy
            self.policy = np.array(target_state.state_vector['policy'])
            print(f"✓ Policy recovered to: {target_state.state_id}")
            print(f"  Restored avg reward: {target_state.state_vector['avg_reward']:.4f}")
    
    def train(self, num_episodes: int = 1000, learning_rate: float = 0.01):
        """
        Train agent with policy gradient updates.
        
        Args:
            num_episodes: Number of episodes to train
            learning_rate: Learning rate for policy updates
        """
        print(f"Training RL agent for {num_episodes} episodes...")
        
        for episode in range(num_episodes):
            # Run episode
            reward = self.run_episode(env_noise=0.1)
            
            # Policy gradient update (simplified)
            gradient = np.random.randn(self.policy_dim) * (reward / 10.0)
            self.policy += learning_rate * gradient
            
            # Add occasional catastrophic failure to test recovery
            if episode % 200 == 199:
                # Simulate catastrophic failure
                self.policy = np.random.randn(self.policy_dim) * 10.0
                print(f"\n⚠️  Catastrophic policy failure at episode {episode + 1}")
            
            if (episode + 1) % 100 == 0:
                avg_reward = np.mean(self.episode_rewards[-100:])
                print(f"Episode {episode + 1}: Avg Reward = {avg_reward:.4f}, Recoveries = {len(self.recovery.recall_history)}")
    
    def get_training_summary(self) -> dict:
        """Get training summary."""
        return {
            'total_episodes': self.episode_count,
            'final_avg_reward': np.mean(self.episode_rewards[-100:]) if self.episode_rewards else 0.0,
            'best_avg_reward': np.mean(self.episode_rewards[max(0, self.episode_count-100):self.episode_count]),
            'total_policy_recoveries': len(self.recovery.recall_history),
            'best_policy_performance': self.recovery.states[self.recovery.best_state_id].performance_metric 
                                       if self.recovery.best_state_id else None
        }


if __name__ == "__main__":
    agent = RLPolicyRecovery(policy_dim=10, decay_constant=500)
    agent.train(num_episodes=1000, learning_rate=0.01)
    
    summary = agent.get_training_summary()
    
    print("\n" + "="*60)
    print("RL POLICY RECOVERY TRAINING COMPLETE")
    print("="*60)
    print(f"Total Episodes: {summary['total_episodes']}")
    print(f"Final Avg Reward: {summary['final_avg_reward']:.4f}")
    print(f"Best Avg Reward: {summary['best_avg_reward']:.4f}")
    print(f"Total Policy Recoveries: {summary['total_policy_recoveries']}")
    print(f"Best Policy Performance: {summary['best_policy_performance']:.4f}")
