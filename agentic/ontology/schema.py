"""
RDF/OWL 온톨로지(ontology.ttl)를 Prolog 사실로 변환한다.

계층 구조의 정본은 ontology.ttl 하나뿐이며, Prolog 가 읽는 is_a/2 사실은
이 모듈이 생성한다. 계층을 두 곳에 기록하지 않기 위한 구조다.
"""
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
ONTOLOGY_TTL = os.path.join(_HERE, "ontology.ttl")
GENERATED_PL = os.path.join(_HERE, "generated", "ontology_facts.pl")


def _local_name(uri) -> str:
    """URI 에서 '#' 뒤의 지역 이름만 추출한다."""
    return str(uri).rsplit("#", 1)[-1]


def to_atom(class_name: str) -> str:
    """CamelCase 클래스명을 Prolog snake_case 아톰으로 변환한다."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()


def load_hierarchy(ttl_path: str = ONTOLOGY_TTL) -> dict[str, list[str]]:
    """
    ttl 을 읽어 {하위아톰: [상위아톰, ...]} 형태의 계층 사전을 만든다.

    직접 상위만 담는다. 이행 관계는 Prolog 의 kind_of/2 가 처리한다.
    """
    from rdflib import Graph, RDFS

    g = Graph()
    g.parse(ttl_path, format="turtle")

    hierarchy: dict[str, list[str]] = {}
    for sub, sup in g.subject_objects(RDFS.subClassOf):
        s = to_atom(_local_name(sub))
        p = to_atom(_local_name(sup))
        hierarchy.setdefault(s, [])
        if p not in hierarchy[s]:
            hierarchy[s].append(p)
    for key in hierarchy:
        hierarchy[key].sort()
    return hierarchy


def find_cycles(hierarchy: dict[str, list[str]]) -> list[list[str]]:
    """계층에 순환이 있으면 순환 경로 목록을 반환한다. 없으면 빈 리스트."""
    cycles: list[list[str]] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {}

    def visit(node: str, path: list[str]) -> None:
        color[node] = GRAY
        for parent in hierarchy.get(node, []):
            state = color.get(parent, WHITE)
            if state == GRAY:
                cycles.append(path + [node, parent])
            elif state == WHITE:
                visit(parent, path + [node])
        color[node] = BLACK

    for node in hierarchy:
        if color.get(node, WHITE) == WHITE:
            visit(node, [])
    return cycles


def ttl_to_prolog(ttl_path: str = ONTOLOGY_TTL, out_path: str = GENERATED_PL) -> int:
    """
    ttl 의 rdfs:subClassOf 를 is_a/2 Prolog 사실로 변환해 파일로 쓴다.

    Returns:
        생성된 is_a/2 사실의 개수

    Raises:
        ValueError: 계층에 순환이 있을 때
    """
    hierarchy = load_hierarchy(ttl_path)

    cycles = find_cycles(hierarchy)
    if cycles:
        raise ValueError(f"온톨로지 계층에 순환이 있습니다: {cycles}")

    lines = [
        "% 이 파일은 schema.py 가 ontology.ttl 로부터 생성했습니다.",
        "% 직접 수정하지 마십시오. ontology.ttl 을 고치고 재생성하십시오.",
        "",
        ":- dynamic is_a/2.",
        "",
    ]
    count = 0
    for sub in sorted(hierarchy):
        for sup in hierarchy[sub]:
            lines.append(f"is_a({sub}, {sup}).")
            count += 1

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return count


if __name__ == "__main__":
    n = ttl_to_prolog()
    print(f"{GENERATED_PL} 에 is_a/2 사실 {n}개를 생성했습니다.")
