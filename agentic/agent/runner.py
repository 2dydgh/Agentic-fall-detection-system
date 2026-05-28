"""
비동기 Agent 실행기.
ActionNode에서 호출하면, 별도 스레드에서 EscalationAgent를 실행한다.
실시간 파이프라인을 블로킹하지 않는다.
결과는 agent_results DB 테이블에 영속 저장된다.
"""
import json
import sqlite3
import threading
from datetime import datetime
from .escalation_agent import EscalationAgent


def _init_agent_results_table(db_path: str) -> None:
    """agent_results 테이블 생성 (없으면)"""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            escalation_needed INTEGER DEFAULT 0,
            final_assessment TEXT,
            actions_taken TEXT
        )
    """)
    conn.commit()
    conn.close()


class AgentRunner:
    """비동기(스레드 기반) Agent 디스패처"""

    # MEDIUM 이상일 때만 Agent 실행
    MIN_SEVERITY_FOR_AGENT = {"MEDIUM", "HIGH"}

    def __init__(self, db_path: str, skip_llm: bool = False, max_iterations: int = 4):
        self._db_path = db_path
        self._skip_llm = skip_llm
        self._max_iterations = max_iterations
        self._results: list[dict] = []
        self._results_lock = threading.Lock()
        self._threads: list[threading.Thread] = []
        _init_agent_results_table(db_path)

    def dispatch(self, context: dict) -> None:
        """
        인시던트 컨텍스트를 받아 비동기로 Agent를 실행한다.
        LOW severity는 무시한다.
        """
        severity = context.get("severity", "LOW")
        if severity not in self.MIN_SEVERITY_FOR_AGENT:
            return

        # db_path 주입
        ctx = {**context, "db_path": self._db_path}

        thread = threading.Thread(
            target=self._run_agent,
            args=(ctx,),
            daemon=True,
        )
        self._threads.append(thread)
        thread.start()

    def _run_agent(self, context: dict) -> None:
        """스레드에서 실행되는 Agent"""
        try:
            agent = EscalationAgent(
                skip_llm=self._skip_llm,
                max_iterations=self._max_iterations,
            )
            result = agent.run(context)
            incident_id = context.get("incident_id", "UNKNOWN")

            # DB에 영속 저장
            self._save_to_db(incident_id, result)

            # 메모리 캐시에도 저장 (빠른 조회용)
            with self._results_lock:
                self._results.append({
                    "incident_id": incident_id,
                    **result,
                })
            print(f"[AgentRunner] Completed: {incident_id} -> {result.get('final_assessment', '')[:80]}")
        except Exception as e:
            print(f"[AgentRunner] Error: {e}")

    def _save_to_db(self, incident_id: str, result: dict) -> None:
        """Agent 결과를 DB에 저장"""
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT INTO agent_results (incident_id, timestamp, escalation_needed, final_assessment, actions_taken) VALUES (?,?,?,?,?)",
            (
                incident_id,
                datetime.now().isoformat(),
                1 if result.get("escalation_needed") else 0,
                result.get("final_assessment", ""),
                json.dumps(result.get("actions_taken", []), default=str),
            )
        )
        conn.commit()
        conn.close()

    def get_results(self) -> list[dict]:
        """완료된 Agent 결과 목록 반환 (메모리 캐시)"""
        with self._results_lock:
            return list(self._results)

    def get_results_from_db(self, limit: int = 20) -> list[dict]:
        """DB에서 Agent 결과 조회 (영속 데이터, 서버 재시작 후에도 유지)"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM agent_results ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            d["escalation_needed"] = bool(d.get("escalation_needed", 0))
            d["actions_taken"] = json.loads(d.get("actions_taken", "[]"))
            results.append(d)
        return results

    def wait_all(self, timeout: float = 10.0) -> None:
        """모든 실행 중인 Agent 스레드가 완료될 때까지 대기 (테스트용)"""
        for t in self._threads:
            t.join(timeout=timeout)
