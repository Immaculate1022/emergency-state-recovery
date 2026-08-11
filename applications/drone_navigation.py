"""
Autonomous Drone Navigation with Emergency State Recovery

Application of Emergency State Recovery to autonomous navigation.
Recovers from sensor confusion and navigation errors by rolling back
to last known good position and orientation.
"""

import sys
sys.path.insert(0, '/home/ubuntu/emergency-state-recovery')

from core.state_recovery import EmergencyStateRecovery
import numpy as np
import math


class DroneNavigationRecovery:
    """
    Drone with emergency navigation recovery.
    """
    
    def __init__(self, decay_constant: int = 500):
        """
        Initialize drone with recovery system.
        
        Args:
            decay_constant: Confidence decay time constant
        """
        self.position = np.array([0.0, 0.0, 0.0])  # x, y, z
        self.orientation = np.array([0.0, 0.0, 0.0])  # roll, pitch, yaw
        self.velocity = np.array([0.0, 0.0, 0.0])
        
        self.recovery = EmergencyStateRecovery(decay_constant=decay_constant, instability_threshold=0.25)
        self.navigation_history = []
        self.step_count = 0
        
        # Record initial state
        self._record_nav_checkpoint("initial_position")
    
    def _calculate_stability_metric(self) -> float:
        """
        Calculate navigation stability metric.
        
        Returns:
            Stability score (0-1, higher is more stable)
        """
        # Stability based on:
        # 1. Low velocity variance (smooth flight)
        # 2. Consistent orientation (no tumbling)
        # 3. Altitude maintenance
        
        velocity_magnitude = np.linalg.norm(self.velocity)
        orientation_magnitude = np.linalg.norm(self.orientation)
        altitude_error = abs(self.position[2] - 10.0)  # Target altitude 10m
        
        # Penalize high velocity variance and orientation changes
        stability = 1.0 / (1.0 + velocity_magnitude + orientation_magnitude + altitude_error)
        
        return stability
    
    def _record_nav_checkpoint(self, label: str):
        \"\"\"Record current navigation state.\"\"\"
        state_id = f\"nav_{label}_{self.step_count}\"
        
        stability = self._calculate_stability_metric()
        
        state_vector = {
            'position': self.position.copy().tolist(),
            'orientation': self.orientation.copy().tolist(),
            'velocity': self.velocity.copy().tolist(),
            'stability': stability
        }
        
        self.recovery.record_state(
            state_id=state_id,
            performance_metric=stability,
            state_vector=state_vector,
            metadata={'label': label}
        )
    
    def update_navigation(self, command: np.ndarray, sensor_noise: float = 0.01):
        \"\"\"
        Update drone position and orientation based on command.
        
        Args:
            command: Navigation command [vx, vy, vz, roll, pitch, yaw]
            sensor_noise: Sensor noise level
        \"\"\"
        # Apply command with noise
        self.velocity = command[:3] + np.random.randn(3) * sensor_noise
        self.orientation = command[3:6] + np.random.randn(3) * sensor_noise
        
        # Update position
        self.position += self.velocity * 0.1  # dt = 0.1
        
        # Simulate altitude maintenance
        if self.position[2] < 0:
            self.position[2] = 0  # Ground collision
        
        self.step_count += 1
        self.navigation_history.append({
            'step': self.step_count,
            'position': self.position.copy(),
            'stability': self._calculate_stability_metric()
        })
        
        # Check stability
        stability = self._calculate_stability_metric()
        is_stable = self.recovery.check_stability(stability)
        
        if not is_stable:
            self._trigger_navigation_recovery()
        elif self.step_count % 50 == 0:
            self._record_nav_checkpoint(f\"step_{self.step_count}\")
    
    def _trigger_navigation_recovery(self):
        \"\"\"Trigger emergency navigation recovery.\"\"\"
        current_stability = self._calculate_stability_metric()
        
        target_state = self.recovery.trigger_recall(
            reason=\"Navigation instability detected\",
            diagnostics={
                'current_stability': current_stability,
                'position': self.position.tolist(),
                'step': self.step_count
            }
        )
        
        if target_state:
            # Restore navigation state
            self.position = np.array(target_state.state_vector['position'])
            self.orientation = np.array(target_state.state_vector['orientation'])
            self.velocity = np.array(target_state.state_vector['velocity'])
            
            print(f\"✓ Navigation recovered to: {target_state.state_id}\")
            print(f\"  Restored position: {self.position}\")
            print(f\"  Restored stability: {target_state.state_vector['stability']:.4f}\")
    
    def simulate_mission(self, num_steps: int = 500, fog_probability: float = 0.1):
        \"\"\"
        Simulate drone mission with environmental challenges.
        
        Args:
            num_steps: Number of navigation steps
            fog_probability: Probability of sensor fog (confusion)
        \"\"\"
        print(f\"Starting drone mission simulation ({num_steps} steps)...\")
        
        for step in range(num_steps):
            # Generate navigation command
            if step < 100:
                # Takeoff phase
                command = np.array([0.0, 0.0, 0.1, 0.0, 0.0, 0.0])
            elif step < 300:
                # Cruise phase
                command = np.array([0.1, 0.05, 0.0, 0.0, 0.0, 0.01])
            else:
                # Landing phase
                command = np.array([0.0, 0.0, -0.05, 0.0, 0.0, 0.0])
            
            # Simulate sensor fog (confusion)
            if np.random.rand() < fog_probability:
                # Sensor malfunction - incorrect readings
                command += np.random.randn(6) * 0.5
                print(f\"\\n⚠️  Sensor fog detected at step {step}\")
            
            self.update_navigation(command, sensor_noise=0.01)
            
            if (step + 1) % 100 == 0:
                stability = self._calculate_stability_metric()
                print(f\"Step {step + 1}: Position = {self.position}, Stability = {stability:.4f}, Recoveries = {len(self.recovery.recall_history)}\")
    
    def get_mission_summary(self) -> dict:
        \"\"\"Get mission summary.\"\"\"
        final_stability = self._calculate_stability_metric()
        avg_stability = np.mean([h['stability'] for h in self.navigation_history[-100:]])
        
        return {
            'total_steps': self.step_count,
            'final_position': self.position.tolist(),
            'final_stability': final_stability,
            'avg_stability': avg_stability,
            'total_recoveries': len(self.recovery.recall_history),
            'best_stability': self.recovery.states[self.recovery.best_state_id].performance_metric 
                             if self.recovery.best_state_id else None
        }


if __name__ == \"__main__\":
    drone = DroneNavigationRecovery(decay_constant=500)
    drone.simulate_mission(num_steps=500, fog_probability=0.05)
    
    summary = drone.get_mission_summary()
    
    print(\"\\n\" + \"=\"*60)
    print(\"DRONE MISSION SIMULATION COMPLETE\")
    print(\"=\"*60)
    print(f\"Total Steps: {summary['total_steps']}\")
    print(f\"Final Position: {summary['final_position']}\")
    print(f\"Final Stability: {summary['final_stability']:.4f}\")
    print(f\"Average Stability: {summary['avg_stability']:.4f}\")
    print(f\"Total Emergency Recoveries: {summary['total_recoveries']}\")
    print(f\"Best Recorded Stability: {summary['best_stability']:.4f}\")
