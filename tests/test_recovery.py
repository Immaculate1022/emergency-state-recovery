import pytest

from core.state_recovery import EmergencyStateRecovery, MultiSystemRecovery


def test_constructor_rejects_invalid_configuration():
    with pytest.raises(ValueError, match="decay_constant"):
        EmergencyStateRecovery(decay_constant=0)
    with pytest.raises(ValueError, match="instability_threshold"):
        EmergencyStateRecovery(instability_threshold=1)


def test_replacing_best_state_recomputes_best_state():
    engine = EmergencyStateRecovery()
    engine.record_state("best", 1.0, {"value": 1})
    engine.record_state("fallback", 0.8, {"value": 0.8})

    engine.record_state("best", 0.2, {"value": 0.2})

    assert engine.best_state_id == "fallback"


def test_export_import_round_trip_includes_history(tmp_path):
    engine = EmergencyStateRecovery()
    engine.record_state("stable", 0.9, {"value": 0.9}, {"source": "test"})
    engine.trigger_recall("regression test", {"severity": "low"})
    path = tmp_path / "states.json"
    engine.export_states(path)

    restored = EmergencyStateRecovery()
    restored.import_states(path)

    assert restored.best_state_id == "stable"
    assert restored.current_step == engine.current_step
    assert restored.states["stable"].metadata == {"source": "test"}
    assert len(restored.recall_history) == 1
    assert restored.recall_history[0].reason == "regression test"


def test_import_does_not_retain_old_states(tmp_path):
    source = EmergencyStateRecovery()
    source.record_state("only-state", 0.5, {})
    path = tmp_path / "states.json"
    source.export_states(path)

    target = EmergencyStateRecovery()
    target.record_state("stale-state", 1.0, {})
    target.import_states(path)

    assert set(target.states) == {"only-state"}


def test_global_realignments_are_safe_for_empty_systems():
    coordinator = MultiSystemRecovery()
    coordinator.register_system("empty", EmergencyStateRecovery())

    assert coordinator.trigger_global_realignment("test") == {
        "empty": {"target_state": None, "confidence": 0.0}
    }
