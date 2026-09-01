import threading

from agentic.ontology.engine import PrologEngine


class TestBasicJudgement:
    def setup_method(self):
        self.engine = PrologEngine()

    def test_high_risk_zone_long_immobility_is_high(self):
        j = self.engine.judge([
            "occurred_in(current, bathroom)",
            "no_movement_duration(current, 45)",
        ])
        assert j.severity == "HIGH"
        assert "r1" in [r.rule_id for r in j.fired_rules]

    def test_ontology_inference_reaches_high_risk_zone(self):
        """bathroom 은 high_risk_zone 이라고 명시되지 않았지만 추론되어야 한다."""
        j = self.engine.judge([
            "occurred_in(current, bathroom)",
            "no_movement_duration(current, 45)",
        ])
        assert j.severity == "HIGH"

    def test_normal_zone_short_immobility_is_low(self):
        j = self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 5)",
        ])
        assert j.severity == "LOW"
        assert j.fired_rules == []

    def test_fired_rule_has_description(self):
        j = self.engine.judge([
            "occurred_in(current, stairs)",
            "no_movement_duration(current, 40)",
        ])
        r = [x for x in j.fired_rules if x.rule_id == "r1"][0]
        assert isinstance(r.description, str) and r.description

    def test_low_severity_gets_log_action_only(self):
        j = self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 1)",
        ])
        assert j.actions == ["log_to_db"]

    def test_high_severity_gets_full_action_set(self):
        j = self.engine.judge([
            "occurred_in(current, bathroom)",
            "no_movement_duration(current, 45)",
        ])
        assert j.actions == [
            "log_to_db",
            "save_snapshot",
            "notify_security_room",
            "send_email_alert",
            "generate_report",
        ]

    def test_facts_are_returned_for_audit(self):
        facts = [
            "occurred_in(current, bathroom)",
            "no_movement_duration(current, 45)",
        ]
        j = self.engine.judge(facts)
        assert j.facts == facts


class TestFactIsolation:
    """엔진이 장기 실행되므로 이전 판정의 사실이 남으면 안 된다."""

    def setup_method(self):
        self.engine = PrologEngine()

    def test_previous_incident_does_not_leak(self):
        self.engine.judge([
            "occurred_in(current, bathroom)",
            "no_movement_duration(current, 45)",
        ])
        j = self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 2)",
        ])
        assert j.severity == "LOW", "이전 사건의 사실이 남아 있음"
        assert j.fired_rules == []

    def test_repeated_identical_queries_are_stable(self):
        facts = [
            "occurred_in(current, bathroom)",
            "no_movement_duration(current, 45)",
        ]
        results = [self.engine.judge(list(facts)).severity for _ in range(10)]
        assert set(results) == {"HIGH"}


class TestThreadSafety:
    def test_four_threads_fifty_queries_each(self):
        engine = PrologEngine()
        errors: list[str] = []
        results: list[str] = []

        def worker(n: int) -> None:
            try:
                for _ in range(50):
                    j = engine.judge([
                        "occurred_in(current, bathroom)",
                        "no_movement_duration(current, 45)",
                    ])
                    results.append(j.severity)
            except Exception as e:                      # noqa: BLE001
                errors.append(f"T{n}: {type(e).__name__}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(results) == 200
        assert set(results) == {"HIGH"}
