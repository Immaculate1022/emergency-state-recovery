"""
Emergency State Recovery Engine

Core module implementing memory-recall alignment, confidence decay,
and automatic rollback to known high-performance states.
"""

import json
import time
import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StateSnapshot:
    """Represents a recorded system state."""
    state_id: str
    timestamp: float
    step_count: int
    performance_metric: float
    state_vector: Dict[str, Any]
    metadata: Dict[str, Any]
    confidence_score: float = 1.0
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)


@dataclass
class RecallEvent:
    """Represents a state recovery event."""
    event_id: str
    timestamp: float
    reason: str
    source_state_id: str
    target_state_id: str
    confidence_decay: float
    diagnostics: Dict[str, Any]
    success: bool
    

class EmergencyStateRecovery:
    """
    Core Emergency State Recovery engine.
    
    Manages state snapshots, monitors system stability, and triggers
    automatic rollback to known high-performance states when instability
    is detected.
    """
    
    def __init__(self, decay_constant: float = 500, instability_threshold: float = 0.3):
        """
        Initialize the recovery engine.
        
        Args:
            decay_constant: Time constant for confidence decay (steps)
            instability_threshold: Threshold for triggering recovery
        """
        if decay_constant <= 0:
            raise ValueError("decay_constant must be greater than zero")
        if not 0 <= instability_threshold < 1:
            raise ValueError("instability_threshold must be in the range [0, 1)")

        self.decay_constant = decay_constant
        self.instability_threshold = instability_threshold
        
        self.states: Dict[str, StateSnapshot] = {}
        self.best_state_id: Optional[str] = None
        self.current_step: int = 0
        self.recall_history: List[RecallEvent] = []
        
    def record_state(self, state_id: str, performance_metric: float, 
                    state_vector: Dict[str, Any], metadata: Dict[str, Any] = None) -> StateSnapshot:
        """
        Record a system state snapshot.
        
        Args:
            state_id: Unique identifier for this state
            performance_metric: Performance score (higher is better)
            state_vector: Full state representation
            metadata: Additional context
            
        Returns:
            StateSnapshot object
        """
        snapshot = StateSnapshot(
            state_id=state_id,
            timestamp=time.time(),
            step_count=self.current_step,
            performance_metric=performance_metric,
            state_vector=state_vector.copy(),
            metadata=(metadata or {}).copy(),
            confidence_score=1.0
        )
        
        self.states[state_id] = snapshot

        previous_best = self.best_state_id
        self.best_state_id = max(
            self.states,
            key=lambda candidate_id: self.states[candidate_id].performance_metric,
        )
        if self.best_state_id != previous_best:
            logger.info(
                f"New best state recorded: {self.best_state_id} "
                f"(performance: {self.states[self.best_state_id].performance_metric:.4f})"
            )

        self.current_step += 1
        return snapshot
    
    def calculate_confidence(self, state_id: str) -> float:
        """
        Calculate confidence score for a state using exponential decay.
        
        conf = exp(-stepsSinceBest / decay_constant)
        
        Args:
            state_id: State to evaluate
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        if state_id not in self.states:
            return 0.0
        
        if self.best_state_id is None:
            return 1.0
        
        best_state = self.states[self.best_state_id]
        target_state = self.states[state_id]
        
        steps_since_best = best_state.step_count - target_state.step_count
        
        if steps_since_best < 0:
            return 1.0
        
        confidence = math.exp(-steps_since_best / self.decay_constant)
        return confidence
    
    def check_stability(self, current_performance: float) -> bool:
        """
        Check if system is stable based on current performance.
        
        Args:
            current_performance: Current performance metric
            
        Returns:
            True if stable, False if unstable
        """
        if self.best_state_id is None:
            return True
        
        best_performance = self.states[self.best_state_id].performance_metric
        
        # System is unstable if performance drops below threshold
        performance_ratio = current_performance / (best_performance + 1e-6)
        
        return performance_ratio > (1.0 - self.instability_threshold)
    
    def trigger_recall(self, reason: str, diagnostics: Dict[str, Any] = None) -> Optional[StateSnapshot]:
        """
        Trigger emergency state recovery.
        
        Finds the best high-confidence state and returns it for rollback.
        
        Args:
            reason: Reason for triggering recall
            diagnostics: Diagnostic information
            
        Returns:
            StateSnapshot to rollback to, or None if no suitable state found
        """
        if not self.states:
            logger.warning("No states available for recall")
            return None
        
        # Find best state with acceptable confidence
        best_candidate = None
        best_score = -float('inf')
        
        for state_id, snapshot in self.states.items():
            confidence = self.calculate_confidence(state_id)
            
            # Score = performance * confidence (prefer high performance + high confidence)
            score = snapshot.performance_metric * confidence
            
            if score > best_score and confidence > 0.1:  # Minimum confidence threshold
                best_score = score
                best_candidate = snapshot
        
        if best_candidate is None:
            logger.error("No suitable state found for recovery")
            return None
        
        # Record recall event
        event = RecallEvent(
            event_id=f"recall_{int(time.time() * 1000)}",
            timestamp=time.time(),
            reason=reason,
            source_state_id=self.best_state_id or "unknown",
            target_state_id=best_candidate.state_id,
            confidence_decay=self.calculate_confidence(best_candidate.state_id),
            diagnostics=diagnostics or {},
            success=True
        )
        
        self.recall_history.append(event)
        
        logger.info(
            f"Emergency recall triggered: {reason}\n"
            f"  Rolling back to state: {best_candidate.state_id}\n"
            f"  Confidence: {event.confidence_decay:.3f}\n"
            f"  Performance: {best_candidate.performance_metric:.4f}"
        )
        
        return best_candidate
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Generate comprehensive diagnostic report.
        
        Returns:
            Dictionary with system diagnostics
        """
        return {
            'total_states_recorded': len(self.states),
            'best_state_id': self.best_state_id,
            'best_state_performance': self.states[self.best_state_id].performance_metric if self.best_state_id else None,
            'current_step': self.current_step,
            'total_recalls': len(self.recall_history),
            'decay_constant': self.decay_constant,
            'instability_threshold': self.instability_threshold,
            'state_confidences': {
                state_id: self.calculate_confidence(state_id)
                for state_id in self.states.keys()
            },
            'recall_history': [asdict(event) for event in self.recall_history[-10:]]  # Last 10 recalls
        }
    
    def export_states(self, filepath: str):
        """Export all states to JSON file."""
        data = {
            'best_state_id': self.best_state_id,
            'current_step': self.current_step,
            'states': {state_id: snapshot.to_dict() for state_id, snapshot in self.states.items()},
            'recall_history': [asdict(event) for event in self.recall_history]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"States exported to {filepath}")
    
    def import_states(self, filepath: str):
        """Import states from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.states = {
            state_id: StateSnapshot.from_dict(state_data)
            for state_id, state_data in data.get('states', {}).items()
        }
        self.current_step = data.get('current_step', 0)
        self.recall_history = [
            RecallEvent(**event_data)
            for event_data in data.get('recall_history', [])
        ]

        requested_best = data.get('best_state_id')
        if requested_best in self.states:
            self.best_state_id = requested_best
        elif self.states:
            self.best_state_id = max(
                self.states,
                key=lambda state_id: self.states[state_id].performance_metric,
            )
        else:
            self.best_state_id = None

        logger.info(f"States imported from {filepath}")


class MultiSystemRecovery:
    """
    Manages recovery across multiple interconnected systems.
    
    Implements "Master Controller" concept for coordinated recovery.
    """
    
    def __init__(self):
        self.systems: Dict[str, EmergencyStateRecovery] = {}
        self.global_best_state: Optional[str] = None
        self.coordination_history: List[Dict] = []
    
    def register_system(self, system_name: str, recovery_engine: EmergencyStateRecovery):
        """Register a system for coordinated recovery."""
        self.systems[system_name] = recovery_engine
        logger.info(f"System registered: {system_name}")
    
    def trigger_global_realignment(self, reason: str = "Global instability detected"):
        """
        Trigger coordinated recovery across all systems.
        
        When multiple systems experience instability simultaneously,
        force global re-alignment to known stable configuration.
        """
        results = {}
        
        for system_name, engine in self.systems.items():
            target_state = engine.trigger_recall(f"Global realignment: {reason}")
            results[system_name] = {
                'target_state': target_state.state_id if target_state else None,
                'confidence': engine.calculate_confidence(target_state.state_id) if target_state else 0.0
            }
        
        event = {
            'timestamp': time.time(),
            'reason': reason,
            'results': results
        }
        
        self.coordination_history.append(event)
        logger.info(f"Global realignment completed: {reason}")
        
        return results
    
    def get_system_health(self) -> Dict[str, Dict]:
        """Get health status of all registered systems."""
        health = {}
        
        for system_name, engine in self.systems.items():
            best_state = engine.states.get(engine.best_state_id) if engine.best_state_id else None
            health[system_name] = {
                'total_states': len(engine.states),
                'best_performance': best_state.performance_metric if best_state else None,
                'total_recalls': len(engine.recall_history),
                'last_recall': engine.recall_history[-1].timestamp if engine.recall_history else None
            }
        
        return health


if __name__ == "__main__":
    # Example usage
    recovery = EmergencyStateRecovery(decay_constant=500, instability_threshold=0.3)
    
    # Simulate recording states
    for i in range(100):
        performance = 0.8 + 0.1 * math.sin(i / 10)
        state_vector = {'iteration': i, 'value': performance}
        recovery.record_state(f"state_{i}", performance, state_vector)
    
    # Simulate instability and trigger recall
    print("\n--- Triggering Emergency Recovery ---")
    target = recovery.trigger_recall("Performance degradation detected", {'error_rate': 0.45})
    
    if target:
        print(f"Recovery target: {target.state_id}")
        print(f"Performance: {target.performance_metric:.4f}")
    
    # Print diagnostics
    print("\n--- System Diagnostics ---")
    diag = recovery.get_diagnostics()
    print(json.dumps(diag, indent=2, default=str))
