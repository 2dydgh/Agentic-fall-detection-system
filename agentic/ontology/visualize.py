"""
온톨로지 계층을 Mermaid 다이어그램으로 출력한다.

    python -m agentic.ontology.visualize

GitHub 은 마크다운의 ```mermaid 블록을 그대로 렌더링하므로 이미지 파일이
필요 없다. 계층이 바뀌면 재실행해서 README 블록을 갱신한다.
"""
from .schema import ONTOLOGY_TTL, load_hierarchy


def to_mermaid(ttl_path: str = ONTOLOGY_TTL) -> str:
    """계층 사전을 Mermaid flowchart 문자열로 변환한다."""
    hierarchy = load_hierarchy(ttl_path)
    lines = ["flowchart TD"]
    for sub in sorted(hierarchy):
        for sup in hierarchy[sub]:
            lines.append(f"    {sup} --> {sub}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("```mermaid")
    print(to_mermaid())
    print("```")
