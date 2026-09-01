from agentic.ontology.facts import posture_of, state_to_facts


class TestPostureOf:
    def test_seventy_degrees_is_collapsed(self):
        assert posture_of(70) == "collapsed"

    def test_just_below_seventy_is_leaning(self):
        assert posture_of(69.9) == "leaning"

    def test_forty_five_is_leaning(self):
        assert posture_of(45) == "leaning"

    def test_just_below_forty_five_is_upright(self):
        assert posture_of(44.9) == "upright"


class TestStateToFacts:
    def _base_state(self, **overrides):
        state = {
            "fall_detected": True,
            "no_movement_seconds": 40.0,
            "estimated_age": "adult",
            "location_type": "other",
            "hazards_detected": [],
            "pose_data": {"angle": 75, "velocity": 20},
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
        }
        state.update(overrides)
        return state

    def test_maps_bathroom_zone(self):
        facts = state_to_facts(self._base_state(location_type="bathroom"))
        assert "occurred_in(current, bathroom)" in facts

    def test_maps_other_to_other_zone(self):
        facts = state_to_facts(self._base_state(location_type="other"))
        assert "occurred_in(current, other_zone)" in facts

    def test_maps_unknown_age_to_unknown_person(self):
        facts = state_to_facts(self._base_state(estimated_age="unknown"))
        assert "involves(current, unknown_person)" in facts

    def test_maps_elderly(self):
        facts = state_to_facts(self._base_state(estimated_age="elderly"))
        assert "involves(current, elderly)" in facts

    def test_no_movement_is_integer_seconds(self):
        facts = state_to_facts(self._base_state(no_movement_seconds=45.7))
        assert "no_movement_duration(current, 45)" in facts

    def test_scream_becomes_audio_event(self):
        facts = state_to_facts(self._base_state(audio_scream_detected=True))
        assert "has_audio_event(current, scream)" in facts

    def test_impact_becomes_audio_event(self):
        facts = state_to_facts(self._base_state(audio_impact_detected=True))
        assert "has_audio_event(current, impact_sound)" in facts

    def test_no_audio_event_when_nothing_detected(self):
        facts = state_to_facts(self._base_state())
        assert not any(f.startswith("has_audio_event") for f in facts)

    def test_posture_from_angle(self):
        facts = state_to_facts(self._base_state(pose_data={"angle": 75, "velocity": 0}))
        assert "has_posture(current, collapsed)" in facts

    def test_hazard_is_quoted(self):
        facts = state_to_facts(self._base_state(hazards_detected=["wet floor"]))
        assert "has_hazard(current, 'wet floor')" in facts

    def test_hazard_with_apostrophe_is_escaped(self):
        facts = state_to_facts(self._base_state(hazards_detected=["it's wet"]))
        assert "has_hazard(current, 'it''s wet')" in facts

    def test_no_trailing_period(self):
        for f in state_to_facts(self._base_state()):
            assert not f.endswith("."), f

    def test_custom_incident_id(self):
        facts = state_to_facts(self._base_state(), incident_id="inc001")
        assert "occurred_in(inc001, other_zone)" in facts

    def test_deterministic(self):
        """동일 입력은 항상 동일 사실을 생성한다 (난수 없음)."""
        s = self._base_state()
        assert state_to_facts(dict(s)) == state_to_facts(dict(s))

    def test_missing_keys_use_defaults(self):
        """빈 state 로도 예외 없이 동작해야 한다."""
        facts = state_to_facts({})
        assert "occurred_in(current, other_zone)" in facts
        assert "involves(current, unknown_person)" in facts
        assert "no_movement_duration(current, 0)" in facts
