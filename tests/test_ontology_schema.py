import os
import tempfile

from agentic.ontology.schema import (
    ONTOLOGY_TTL,
    load_hierarchy,
    ttl_to_prolog,
    find_cycles,
)


class TestLoadHierarchy:
    def test_bathroom_is_subclass_of_wet_area(self):
        h = load_hierarchy(ONTOLOGY_TTL)
        assert "wet_area" in h["bathroom"]

    def test_wet_area_is_subclass_of_high_risk_zone(self):
        h = load_hierarchy(ONTOLOGY_TTL)
        assert "high_risk_zone" in h["wet_area"]

    def test_every_vlm_location_value_has_a_class(self):
        """state.py 의 location_type 5개 값이 모두 온톨로지에 존재해야 한다."""
        h = load_hierarchy(ONTOLOGY_TTL)
        known = set(h) | {s for supers in h.values() for s in supers}
        for atom in ("stairs", "bathroom", "hallway", "outdoor", "other_zone"):
            assert atom in known, f"{atom} 이 온톨로지에 없음"

    def test_every_vlm_age_value_has_a_class(self):
        """state.py 의 estimated_age 4개 값이 모두 온톨로지에 존재해야 한다."""
        h = load_hierarchy(ONTOLOGY_TTL)
        known = set(h) | {s for supers in h.values() for s in supers}
        for atom in ("elderly", "child", "adult", "unknown_person"):
            assert atom in known, f"{atom} 이 온톨로지에 없음"

    def test_unclassified_zone_is_not_high_risk(self):
        """야외/기타 구역은 고위험으로 분류되지 않아야 한다."""
        h = load_hierarchy(ONTOLOGY_TTL)
        assert "high_risk_zone" not in h["unclassified_zone"]
        assert "normal_zone" not in h["unclassified_zone"]


class TestFindCycles:
    def test_detects_a_cycle(self):
        assert find_cycles({"a": ["b"], "b": ["c"], "c": ["a"]}) != []

    def test_clean_hierarchy_has_no_cycle(self):
        assert find_cycles({"a": ["b"], "b": ["c"]}) == []

    def test_real_ontology_has_no_cycle(self):
        assert find_cycles(load_hierarchy(ONTOLOGY_TTL)) == []


class TestTtlToProlog:
    def test_writes_prolog_facts(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.pl")
            n = ttl_to_prolog(ONTOLOGY_TTL, out)
            assert n > 0
            text = open(out, encoding="utf-8").read()
            assert ":- dynamic is_a/2." in text
            assert "is_a(bathroom, wet_area)." in text

    def test_returned_count_matches_fact_lines(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.pl")
            n = ttl_to_prolog(ONTOLOGY_TTL, out)
            lines = [
                l for l in open(out, encoding="utf-8").read().splitlines()
                if l.startswith("is_a(")
            ]
            assert len(lines) == n
