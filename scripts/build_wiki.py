"""Build an Obsidian-compatible Markdown wiki from normalized graph CSV files."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
WIKI_DIR = PROJECT_ROOT / "wiki"

TYPE_DIRECTORIES = {
    "RuiRo": "risks",
    "KiemSoat": "controls",
    "SuKienRuiRo": "events",
}
TYPE_TITLES = {
    "RuiRo": "Rủi ro",
    "KiemSoat": "Kiểm soát",
    "SuKienRuiRo": "Sự kiện rủi ro",
}
EXPECTED_RELATION_ENDPOINTS = {
    "MITIGATES": ("KiemSoat", "RuiRo"),
    "OBSERVED_AS": ("RuiRo", "SuKienRuiRo"),
}
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def safe_filename(value: str, fallback: str) -> str:
    filename = re.sub(r'[<>:"/\\|?*\[\]#^]', "-", value)
    filename = re.sub(r"\s+", " ", filename).strip(" .")
    if not filename or filename.upper() in WINDOWS_RESERVED_NAMES:
        filename = fallback
    return filename[:120].rstrip(" .") or fallback


def yaml_value(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def frontmatter(entity: dict[str, str]) -> list[str]:
    return [
        "---",
        f"id: {yaml_value(entity['id'])}",
        f"type: {yaml_value(entity['type'])}",
        f"verification_status: {yaml_value(entity['verification_status'])}",
        f"data_origin: {yaml_value(entity['data_origin'])}",
        "---",
        "",
    ]


def property_section(
    title: str, entity: dict[str, str], fields: list[tuple[str, str]]
) -> list[str]:
    populated = [(label, entity.get(column, "")) for label, column in fields]
    populated = [(label, value) for label, value in populated if value]
    if not populated:
        return []
    lines = [f"## {title}", ""]
    lines.extend(f"- **{label}:** {value}" for label, value in populated)
    lines.append("")
    return lines


def build_page_paths(entities: list[dict[str, str]]) -> dict[str, str]:
    page_paths: dict[str, str] = {}
    used_paths: set[str] = set()
    for entity in entities:
        directory = TYPE_DIRECTORIES[entity["type"]]
        stem = safe_filename(entity.get("name", ""), entity["id"])
        relative_path = f"{directory}/{stem}"
        if relative_path.casefold() in used_paths:
            relative_path = f"{directory}/{stem} - {entity['id']}"
        if relative_path.casefold() in used_paths:
            raise ValueError(f"Không thể tạo tên trang duy nhất cho {entity['id']}")
        used_paths.add(relative_path.casefold())
        page_paths[entity["id"]] = relative_path
    return page_paths


def wikilink(entity: dict[str, str], page_paths: dict[str, str]) -> str:
    return f"[[{page_paths[entity['id']]}|{entity['name']}]]"


def relation_section(
    title: str,
    relation_pairs: list[tuple[dict[str, str], dict[str, str]]],
    page_paths: dict[str, str],
) -> list[str]:
    lines = [f"## {title}", ""]
    if not relation_pairs:
        return lines + ["Không có trong dữ liệu quan hệ hiện tại.", ""]

    for relation, related_entity in relation_pairs:
        lines.extend(
            [
                f"- {wikilink(related_entity, page_paths)}",
                f"  - **relationship_type:** {relation['relationship_type']}",
                f"  - **evidence_quote:** {relation['evidence_quote']}",
                f"  - **verification_status:** {relation['verification_status']}",
            ]
        )
    lines.append("")
    return lines


def entity_page(
    entity: dict[str, str],
    outgoing: list[tuple[dict[str, str], dict[str, str]]],
    incoming: list[tuple[dict[str, str], dict[str, str]]],
    page_paths: dict[str, str],
) -> str:
    lines = frontmatter(entity)
    lines.extend([f"# {entity['name']}", ""])

    if entity["type"] == "RuiRo":
        lines.extend(
            property_section(
                "Thông tin rủi ro",
                entity,
                [
                    ("Mô tả", "description"),
                    ("Phân loại", "category"),
                    ("Nguyên nhân", "cause"),
                    ("Sự kiện", "event"),
                    ("Tác động", "impact"),
                    ("Mức độ vốn có", "inherent_level"),
                    ("Mức độ còn lại", "residual_level"),
                    ("Mã đơn vị sở hữu", "owner_unit_id"),
                ],
            )
        )
        controls = [pair for pair in incoming if pair[0]["relationship_type"] == "MITIGATES"]
        events = [pair for pair in outgoing if pair[0]["relationship_type"] == "OBSERVED_AS"]
        lines.extend(relation_section("Kiểm soát liên quan", controls, page_paths))
        lines.extend(relation_section("Sự kiện liên quan", events, page_paths))
    elif entity["type"] == "KiemSoat":
        lines.extend(
            property_section(
                "Thông tin kiểm soát",
                entity,
                [
                    ("Mô tả", "description"),
                    ("Loại kiểm soát", "control_type"),
                    ("Tần suất", "frequency"),
                    ("Mã vai trò phụ trách", "owner_role_id"),
                    ("Hiệu lực", "effectiveness"),
                ],
            )
        )
        risks = [pair for pair in outgoing if pair[0]["relationship_type"] == "MITIGATES"]
        lines.extend(relation_section("Rủi ro được giảm thiểu", risks, page_paths))
    else:
        lines.extend(
            property_section(
                "Thông tin sự kiện",
                entity,
                [
                    ("Mô tả", "description"),
                    ("Ngày xảy ra", "occurred_at"),
                    ("Ngày phát hiện", "discovered_at"),
                    ("Mức độ", "severity"),
                    ("Tổn thất (VND)", "loss_amount_vnd"),
                ],
            )
        )
        risks = [pair for pair in incoming if pair[0]["relationship_type"] == "OBSERVED_AS"]
        lines.extend(relation_section("Rủi ro liên quan", risks, page_paths))

    return "\n".join(lines).rstrip() + "\n"


def home_page(
    entities: list[dict[str, str]],
    relations: list[dict[str, str]],
    page_paths: dict[str, str],
) -> str:
    lines = ["# Wiki Risk Graph", "", "## Thống kê", ""]
    type_counts = Counter(entity["type"] for entity in entities)
    lines.append(f"- **Tổng số node:** {len(entities)}")
    lines.append(f"- **Tổng số edge:** {len(relations)}")
    for entity_type in TYPE_DIRECTORIES:
        lines.append(f"- **{TYPE_TITLES[entity_type]}:** {type_counts[entity_type]}")
    lines.append("")

    for entity_type in TYPE_DIRECTORIES:
        lines.extend([f"## Danh sách {TYPE_TITLES[entity_type].lower()}", ""])
        typed_entities = [entity for entity in entities if entity["type"] == entity_type]
        for entity in typed_entities:
            lines.append(f"- {wikilink(entity, page_paths)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def validate_graph(
    entities_by_id: dict[str, dict[str, str]], relations: list[dict[str, str]]
) -> None:
    for row_number, relation in enumerate(relations, start=2):
        source = entities_by_id.get(relation.get("source_id", ""))
        target = entities_by_id.get(relation.get("target_id", ""))
        if source is None or target is None:
            raise ValueError(f"Orphan reference tại relations.csv dòng {row_number}")
        expected_types = EXPECTED_RELATION_ENDPOINTS.get(relation["relationship_type"])
        actual_types = (source["type"], target["type"])
        if expected_types is None or actual_types != expected_types:
            raise ValueError(
                f"Quan hệ không được hỗ trợ tại dòng {row_number}: "
                f"{actual_types[0]} -{relation['relationship_type']}-> {actual_types[1]}"
            )


def main() -> None:
    entities = read_csv(OUTPUT_DIR / "entities.csv")
    relations = read_csv(OUTPUT_DIR / "relations.csv")
    entities_by_id = {entity["id"]: entity for entity in entities}
    if len(entities_by_id) != len(entities):
        raise ValueError("entities.csv có ID rỗng hoặc trùng")

    unknown_types = sorted({entity["type"] for entity in entities} - TYPE_DIRECTORIES.keys())
    if unknown_types:
        raise ValueError(f"Loại entity không được hỗ trợ: {unknown_types}")
    validate_graph(entities_by_id, relations)

    page_paths = build_page_paths(entities)
    outgoing: dict[str, list[tuple[dict[str, str], dict[str, str]]]] = defaultdict(list)
    incoming: dict[str, list[tuple[dict[str, str], dict[str, str]]]] = defaultdict(list)
    for relation in relations:
        source = entities_by_id[relation["source_id"]]
        target = entities_by_id[relation["target_id"]]
        outgoing[source["id"]].append((relation, target))
        incoming[target["id"]].append((relation, source))

    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    for directory in TYPE_DIRECTORIES.values():
        target_directory = WIKI_DIR / directory
        target_directory.mkdir(parents=True, exist_ok=True)
        for old_page in target_directory.glob("*.md"):
            old_page.unlink()

    for entity in entities:
        page = entity_page(
            entity,
            outgoing[entity["id"]],
            incoming[entity["id"]],
            page_paths,
        )
        (WIKI_DIR / f"{page_paths[entity['id']]}.md").write_text(page, encoding="utf-8")

    home = home_page(entities, relations, page_paths)
    (WIKI_DIR / "Home.md").write_text(home, encoding="utf-8")

    wiki_pages = list(WIKI_DIR.rglob("*.md"))
    wikilink_count = sum(
        len(re.findall(r"\[\[[^\]]+\]\]", page.read_text(encoding="utf-8")))
        for page in wiki_pages
    )
    example_control = next(
        relation for relation in relations if relation["relationship_type"] == "MITIGATES"
    )
    example_event = next(
        relation
        for relation in relations
        if relation["relationship_type"] == "OBSERVED_AS"
        and relation["source_id"] == example_control["target_id"]
    )
    print(f"Số trang Wiki đã tạo: {len(wiki_pages)}")
    print(f"Số wikilink: {wikilink_count}")
    print("Ví dụ đường đi:")
    print(
        f"  {entities_by_id[example_control['source_id']]['name']} "
        f"-MITIGATES-> {entities_by_id[example_control['target_id']]['name']} "
        f"-OBSERVED_AS-> {entities_by_id[example_event['target_id']]['name']}"
    )


if __name__ == "__main__":
    main()