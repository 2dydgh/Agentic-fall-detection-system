"""
4개 판정 모드를 동일 입력으로 실행해 비교표를 만든다.

    python -m scripts.compare_modes

기존 rule 경로의 난수 때문에 재현성 측정은 각 시나리오를 10회 반복한다.
LLM 모드는 Ollama 가 떠 있어야 하며, 없으면 해당 열을 '실행 불가' 로 표시한다.

ontology 모드는 판정에 과거 사건 이력을 사용하므로, 이 스크립트는 임시 DB 를
직접 만들어 S8 이 필요로 하는 이력 1건만 주입한다. 프로젝트 루트의
`incidents.db` 는 읽지도 쓰지도 않는다 — 그래야 표가 실행 환경이 아니라
코드만의 함수가 된다.
"""
import collections
import contextlib
import os
import shutil
import sqlite3
import statistics
import tempfile
import time
from datetime import datetime, timedelta

from agentic.nodes import decision_ontology
from agentic.nodes.decision import decision_node_attention, decision_node_rule
from agentic.nodes.decision_llm import decision_node_llm
from agentic.nodes.decision_ontology import decision_node_ontology
from agentic.tools.db import init_db

REPEATS = 30
LLM_REPEATS = 3
OUT_PATH = os.path.join("docs", "comparison_results.md")

# S8 이 재낙상으로 판정되려면 필요한 이력. 하루 전으로 잡아
# rules.pl r6/r13 의 30분 하한을 여유 있게 넘긴다.
HISTORY_CAMERA = "99"
HISTORY_AGE = timedelta(days=1)


def _state(**overrides) -> dict:
    base = {
        "fall_detected": True,
        "no_movement_seconds": 0.0,
        "estimated_age": "adult",
        "location_type": "other",
        "hazards_detected": [],
        "pose_data": {"angle": 75, "velocity": 20},
        "audio_scream_detected": False,
        "audio_impact_detected": False,
        "audio_confidence": 0.0,
        "scene_description": "",
        "camera_id": "97",
    }
    base.update(overrides)
    return base


SCENARIOS = [
    {"id": "S1", "desc": "거실, 8초, 성인",
     "state": _state(location_type="other", no_movement_seconds=8.0)},
    {"id": "S2", "desc": "화장실, 45초, 노인",
     "state": _state(location_type="bathroom", no_movement_seconds=45.0,
                     estimated_age="elderly")},
    {"id": "S3", "desc": "복도, 12초, 성인, 비명",
     "state": _state(location_type="hallway", no_movement_seconds=12.0,
                     audio_scream_detected=True, audio_confidence=0.8)},
    {"id": "S4", "desc": "계단, 35초, 성인",
     "state": _state(location_type="stairs", no_movement_seconds=35.0)},
    {"id": "S5", "desc": "거실, 300초, 성인",
     "state": _state(location_type="other", no_movement_seconds=300.0)},
    {"id": "S6", "desc": "화장실, 20초, 아동",
     "state": _state(location_type="bathroom", no_movement_seconds=20.0,
                     estimated_age="child")},
    {"id": "S7", "desc": "경계값 (각도 46, 속도 12, 0초)",
     "state": _state(pose_data={"angle": 46, "velocity": 12},
                     no_movement_seconds=0.0)},
    {"id": "S8", "desc": "복도, 12초 + 3일 내 재낙상",
     "state": _state(location_type="hallway", no_movement_seconds=12.0,
                     camera_id="99")},
    {"id": "S9", "desc": "붕괴자세 + 충격음 + 25초",
     "state": _state(location_type="other", no_movement_seconds=25.0,
                     pose_data={"angle": 80, "velocity": 25},
                     audio_impact_detected=True, audio_confidence=0.7)},
    {"id": "S10", "desc": "위험물 + 붕괴자세",
     "state": _state(location_type="other", no_movement_seconds=5.0,
                     pose_data={"angle": 80, "velocity": 25},
                     hazards_detected=["wet floor"])},
]


@contextlib.contextmanager
def _seeded_history_db():
    """
    S8 용 이력 1건만 담은 임시 DB 를 만들고 온톨로지 노드가 그것을 보게 한다.

    실제 `incidents.db` 를 건드리지 않으므로, 이 스크립트의 출력은 누가 어디서
    돌리든 같다.
    """
    tmpdir = tempfile.mkdtemp(prefix="compare_modes_")
    db_path = os.path.join(tmpdir, "compare_modes.db")
    init_db(db_path)

    when = datetime.now() - HISTORY_AGE
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO incidents (incident_id, camera_id, timestamp, severity, "
            "severity_score, scene_description, actions_taken) VALUES (?,?,?,?,?,?,?)",
            ("INC-SEED-S8", HISTORY_CAMERA, when.isoformat(), "MEDIUM", 60, "", "[]"),
        )
        conn.commit()
    finally:
        conn.close()

    original = decision_ontology.DB_PATH
    decision_ontology.DB_PATH = db_path
    try:
        yield db_path
    finally:
        decision_ontology.DB_PATH = original
        shutil.rmtree(tmpdir, ignore_errors=True)


def _llm_available() -> bool:
    try:
        import ollama

        ollama.list()
        return True
    except Exception:  # noqa: BLE001
        return False


def _run(fn, state: dict, repeats: int = REPEATS) -> dict:
    """한 모드를 repeats 회 실행하고 판정 집합·점수 분포·평균 지연을 모은다."""
    severities, scores, elapsed = [], [], []
    for _ in range(repeats):
        t = time.perf_counter()
        try:
            r = fn(dict(state))
        except Exception as e:  # noqa: BLE001
            return {"severities": {f"ERROR: {type(e).__name__}"},
                    "scores": collections.Counter(), "ms": 0.0}
        elapsed.append((time.perf_counter() - t) * 1000)
        severities.append(r.get("severity"))
        scores.append(r.get("severity_score"))
    return {
        "severities": set(severities),
        "scores": collections.Counter(scores),
        "ms": statistics.mean(elapsed) if elapsed else 0.0,
    }


def main() -> None:
    llm_ok = _llm_available()
    modes = [
        ("rule", decision_node_rule),
        ("attention", decision_node_attention),
        ("ontology", decision_node_ontology),
    ]
    if llm_ok:
        modes.insert(2, ("llm", decision_node_llm))

    lines = ["# 판정 모드 비교 실험 결과", ""]
    lines += [
        "> 이 표는 코드만의 함수입니다. ontology 열이 쓰는 사건 이력은 스크립트가 "
        f"임시 DB 에 직접 주입한 1건(카메라 {HISTORY_CAMERA}, "
        f"{int(HISTORY_AGE.total_seconds() // 3600)}시간 전)뿐이며, "
        "프로젝트 루트의 `incidents.db` 는 읽지도 쓰지도 않습니다.",
        "",
    ]
    if not llm_ok:
        lines += ["> LLM 모드는 Ollama 미실행으로 제외했습니다.", ""]
    if llm_ok:
        lines += [
            f"> LLM 열은 호출 비용이 커서 {LLM_REPEATS}회만 반복했습니다. "
            f"다른 열({REPEATS}회)과 반복 횟수가 다르므로 동일한 표본 수로 "
            "비교하지 마십시오.",
            "",
        ]

    header = "| 시나리오 | 상황 | " + " | ".join(n for n, _ in modes) + " |"
    lines += [header, "|" + "---|" * (len(modes) + 2)]

    llm_scores: collections.Counter = collections.Counter()

    with _seeded_history_db():
        for sc in SCENARIOS:
            cells = []
            for name, fn in modes:
                repeats = LLM_REPEATS if name == "llm" else REPEATS
                res = _run(fn, sc["state"], repeats=repeats)
                if name == "llm":
                    llm_scores.update(res["scores"])
                sev = "/".join(sorted(res["severities"]))
                if name == "ontology":
                    cells.append(f"{sev} (점수 없음)")
                elif len(res["severities"]) > 1:
                    cells.append(f"**{sev}** (비결정적)")
                else:
                    cells.append(sev)
            lines.append(f"| {sc['id']} | {sc['desc']} | " + " | ".join(cells) + " |")

        if llm_ok and llm_scores:
            total = sum(llm_scores.values())
            dist = ", ".join(
                f"{score}점 {n}회" for score, n in sorted(llm_scores.items())
            )
            lines += [
                "",
                f"LLM 자체 점수 분포 (총 {total}회 호출): {dist}",
            ]

        lines += ["", "## 발동 규칙 (ontology 모드)", ""]
        for sc in SCENARIOS:
            r = decision_node_ontology(dict(sc["state"]))
            rules = ", ".join(
                f"`{x['rule_id']}` {x['description']}" for x in r["fired_rules"]
            ) or "없음"
            lines.append(f"- **{sc['id']}** {sc['desc']} → **{r['severity']}** — {rules}")

    text = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n=> {OUT_PATH} 에 저장했습니다.")


if __name__ == "__main__":
    main()
