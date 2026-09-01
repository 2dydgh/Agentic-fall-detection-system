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


class TestHighRules:
    def setup_method(self):
        self.engine = PrologEngine()

    def _ids(self, facts):
        return [r.rule_id for r in self.engine.judge(facts).fired_rules]

    def test_r2_vulnerable_with_scream(self):
        ids = self._ids([
            "occurred_in(current, hallway)",
            "involves(current, elderly)",
            "has_audio_event(current, scream)",
            "no_movement_duration(current, 1)",
        ])
        assert "r2" in ids

    def test_r2_also_fires_for_child(self):
        """아동도 취약 계층이다. 기존 rule 경로는 아동을 성인과 동일 취급한다."""
        ids = self._ids([
            "occurred_in(current, hallway)",
            "involves(current, child)",
            "has_audio_event(current, scream)",
            "no_movement_duration(current, 1)",
        ])
        assert "r2" in ids

    def test_r2_does_not_fire_for_adult(self):
        ids = self._ids([
            "occurred_in(current, hallway)",
            "involves(current, adult)",
            "has_audio_event(current, scream)",
            "no_movement_duration(current, 1)",
        ])
        assert "r2" not in ids

    def test_r3_sixty_seconds_anywhere(self):
        ids = self._ids([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 60)",
        ])
        assert "r3" in ids

    def test_r3_does_not_fire_at_fifty_nine(self):
        ids = self._ids([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 59)",
        ])
        assert "r3" not in ids

    def test_r4_collapsed_impact_twenty_seconds(self):
        ids = self._ids([
            "occurred_in(current, hallway)",
            "has_posture(current, collapsed)",
            "has_audio_event(current, impact_sound)",
            "no_movement_duration(current, 20)",
        ])
        assert "r4" in ids

    def test_r5_vulnerable_in_high_risk_zone(self):
        ids = self._ids([
            "occurred_in(current, bathroom)",
            "involves(current, elderly)",
            "no_movement_duration(current, 15)",
        ])
        assert "r5" in ids


class TestMediumRules:
    def setup_method(self):
        self.engine = PrologEngine()

    def _judge(self, facts):
        return self.engine.judge(facts)

    def test_r7_high_risk_zone_between_ten_and_thirty(self):
        j = self._judge([
            "occurred_in(current, bathroom)",
            "no_movement_duration(current, 20)",
        ])
        assert j.severity == "MEDIUM"
        assert "r7" in [r.rule_id for r in j.fired_rules]

    def test_r7_upper_bound_is_exclusive(self):
        """30초는 r1(HIGH) 영역이므로 r7 은 발동하지 않는다."""
        j = self._judge([
            "occurred_in(current, bathroom)",
            "no_movement_duration(current, 30)",
        ])
        assert j.severity == "HIGH"
        assert "r7" not in [r.rule_id for r in j.fired_rules]

    def test_r8_scream_alone(self):
        j = self._judge([
            "occurred_in(current, hallway)",
            "involves(current, adult)",
            "has_audio_event(current, scream)",
            "no_movement_duration(current, 2)",
        ])
        assert j.severity == "MEDIUM"
        assert "r8" in [r.rule_id for r in j.fired_rules]

    def test_r9_vulnerable_fifteen_seconds(self):
        j = self._judge([
            "occurred_in(current, hallway)",
            "involves(current, elderly)",
            "no_movement_duration(current, 15)",
        ])
        assert "r9" in [r.rule_id for r in j.fired_rules]

    def test_r10_collapsed_ten_seconds(self):
        j = self._judge([
            "occurred_in(current, hallway)",
            "has_posture(current, collapsed)",
            "no_movement_duration(current, 10)",
        ])
        assert "r10" in [r.rule_id for r in j.fired_rules]

    def test_r11_impact_with_collapsed(self):
        j = self._judge([
            "occurred_in(current, hallway)",
            "has_posture(current, collapsed)",
            "has_audio_event(current, impact_sound)",
            "no_movement_duration(current, 1)",
        ])
        assert "r11" in [r.rule_id for r in j.fired_rules]

    def test_r12_hazard_with_collapsed(self):
        j = self._judge([
            "occurred_in(current, hallway)",
            "has_posture(current, collapsed)",
            "has_hazard(current, 'wet floor')",
            "no_movement_duration(current, 1)",
        ])
        assert "r12" in [r.rule_id for r in j.fired_rules]

    def test_high_wins_over_medium(self):
        """HIGH 와 MEDIUM 규칙이 동시에 발동해도 최종 판정은 HIGH."""
        j = self._judge([
            "occurred_in(current, bathroom)",
            "involves(current, elderly)",
            "has_audio_event(current, scream)",
            "no_movement_duration(current, 45)",
        ])
        assert j.severity == "HIGH"
        ids = [r.rule_id for r in j.fired_rules]
        assert "r1" in ids and "r8" in ids


class TestUnclassifiedZone:
    def setup_method(self):
        self.engine = PrologEngine()

    def test_outdoor_does_not_trigger_zone_rules(self):
        """야외는 고위험도 정상도 아니므로 구역 기반 규칙이 발동하지 않는다.

        무동작 40초는 r3(60초 이상)에도 못 미치고, 자세 사실도 없으므로
        아무 규칙도 발동하지 않아야 한다.
        """
        j = self.engine.judge([
            "occurred_in(current, outdoor)",
            "no_movement_duration(current, 40)",
        ])
        assert [r.rule_id for r in j.fired_rules] == []
        assert j.severity == "LOW"


class TestTemporalRules:
    def setup_method(self):
        self.engine = PrologEngine()

    def test_r13_fires_on_repeat_incident(self):
        j = self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 2)",
            "prior_incident('INC-A', '01', 2880)",
        ])
        assert j.severity == "MEDIUM"
        assert "r13" in [r.rule_id for r in j.fired_rules]

    def test_r6_escalates_repeat_with_immobility(self):
        j = self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 12)",
            "prior_incident('INC-A', '01', 1440)",
        ])
        assert j.severity == "HIGH"
        assert "r6" in [r.rule_id for r in j.fired_rules]

    def test_recent_incident_does_not_satisfy_the_thirty_minute_floor(self):
        """5분 전 이력은 '같은 낙상의 재검출' 이므로 시간축 규칙이 발동하면 안 된다."""
        facts = [
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 12)",
            "prior_incident('INC-A', '01', 5)",
        ]
        j = self.engine.judge(facts)
        ids = [r.rule_id for r in j.fired_rules]
        assert "r6" not in ids and "r13" not in ids

    def test_older_incident_does_satisfy_the_floor(self):
        """같은 입력에 이력만 40분 전으로 바꾸면 시간축 규칙이 발동한다."""
        j = self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 12)",
            "prior_incident('INC-A', '01', 40)",
        ])
        ids = [r.rule_id for r in j.fired_rules]
        assert "r6" in ids and "r13" in ids
        assert j.severity == "HIGH"

    def test_floor_boundary_is_inclusive_at_thirty_minutes(self):
        j = self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 2)",
            "prior_incident('INC-A', '01', 30)",
        ])
        assert "r13" in [r.rule_id for r in j.fired_rules]

    def test_floor_boundary_excludes_twenty_nine_minutes(self):
        j = self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 2)",
            "prior_incident('INC-A', '01', 29)",
        ])
        assert j.severity == "LOW"
        assert j.fired_rules == []

    def test_without_history_same_facts_stay_low(self):
        """이력이 없으면 동일 상황이 LOW 다. 이 대비가 시간축 추론의 증거다."""
        j = self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 2)",
        ])
        assert j.severity == "LOW"

    def test_history_does_not_leak_between_judgements(self):
        self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 2)",
            "prior_incident('INC-A', '01', 1440)",
        ])
        j = self.engine.judge([
            "occurred_in(current, hallway)",
            "no_movement_duration(current, 2)",
        ])
        assert j.severity == "LOW", "이전 판정의 이력 사실이 남아 있음"
