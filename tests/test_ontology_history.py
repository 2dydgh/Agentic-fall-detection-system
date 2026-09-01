import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

from agentic.ontology.history import history_facts
from agentic.tools.db import init_db, query_recent_incidents


def _insert(db_path, incident_id, camera_id, when, location_type="bathroom"):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO incidents (incident_id, camera_id, timestamp, severity, "
        "severity_score, scene_description, actions_taken, location_type) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (incident_id, camera_id, when.isoformat(), "HIGH", 90, "", "[]", location_type),
    )
    conn.commit()
    conn.close()


class TestQueryRecentIncidents:
    def setup_method(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.dir.name, "t.db")
        init_db(self.db)
        self.now = datetime(2026, 9, 1, 12, 0, 0)

    def teardown_method(self):
        self.dir.cleanup()

    def test_finds_incident_from_yesterday(self):
        _insert(self.db, "INC-A", "01", self.now - timedelta(days=1))
        rows = query_recent_incidents(self.db, "01", within_days=3, now=self.now)
        assert [r["incident_id"] for r in rows] == ["INC-A"]

    def test_ignores_incident_older_than_window(self):
        _insert(self.db, "INC-OLD", "01", self.now - timedelta(days=10))
        rows = query_recent_incidents(self.db, "01", within_days=3, now=self.now)
        assert rows == []

    def test_ignores_other_camera(self):
        _insert(self.db, "INC-B", "02", self.now - timedelta(days=1))
        rows = query_recent_incidents(self.db, "01", within_days=3, now=self.now)
        assert rows == []

    def test_returns_location_type(self):
        _insert(self.db, "INC-C", "01", self.now - timedelta(hours=2), "stairs")
        rows = query_recent_incidents(self.db, "01", within_days=3, now=self.now)
        assert rows[0]["location_type"] == "stairs"


class TestHistoryFacts:
    def setup_method(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.dir.name, "t.db")
        init_db(self.db)
        self.now = datetime(2026, 9, 1, 12, 0, 0)

    def teardown_method(self):
        self.dir.cleanup()

    def test_generates_prior_incident_fact(self):
        _insert(self.db, "INC-A", "01", self.now - timedelta(days=2))
        facts = history_facts(self.db, "01", within_days=3, now=self.now)
        assert facts == ["prior_incident('INC-A', '01', 2)"]

    def test_same_day_is_zero_days_ago(self):
        _insert(self.db, "INC-A", "01", self.now - timedelta(hours=3))
        facts = history_facts(self.db, "01", within_days=3, now=self.now)
        assert facts == ["prior_incident('INC-A', '01', 0)"]

    def test_no_history_returns_empty(self):
        assert history_facts(self.db, "01", within_days=3, now=self.now) == []

    def test_facts_have_no_trailing_period(self):
        _insert(self.db, "INC-A", "01", self.now - timedelta(days=1))
        for f in history_facts(self.db, "01", within_days=3, now=self.now):
            assert not f.endswith(".")

    def test_missing_db_file_returns_empty(self):
        """DB 가 없어도 판정이 멈추면 안 된다."""
        assert history_facts("/nonexistent/x.db", "01", now=self.now) == []
