"""Normalize Wiki Risk Graph seed data into entity and relation CSV files."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

ENTITY_SOURCES = {
    "risk_profiles_seed.csv": "RuiRo",
    "controls_seed.csv": "KiemSoat",
    "risk_events_seed.csv": "SuKienRuiRo",
}
RELATION_SOURCE = "relationships_seed.csv"
BASE_ENTITY_COLUMNS = [
    "id",
    "type",
    "name",
    "description",
    "source_file",
    "data_origin",
    "verification_status",
]


def read_csv(filename: str) -> tuple[list[str], list[dict[str, str]]]:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError(f"CSV không có dòng tiêu đề: {path}")
        return list(reader.fieldnames), list(reader)


def build_entities() -> tuple[list[str], list[dict[str, str]]]:
    entities: list[dict[str, str]] = []
    business_columns: list[str] = []

    for source_file, entity_type in ENTITY_SOURCES.items():
        source_columns, source_rows = read_csv(source_file)
        for column in source_columns:
            if column not in BASE_ENTITY_COLUMNS and column not in business_columns:
                business_columns.append(column)

        for source_row in source_rows:
            description = source_row.get("description", "")
            entity = dict(source_row)
            entity.update(
                {
                    "id": source_row.get("id", ""),
                    "type": entity_type,
                    "name": source_row.get("name", "") or description,
                    "description": description,
                    "source_file": source_file,
                    "data_origin": source_row.get("data_origin", ""),
                    "verification_status": source_row.get("verification_status", ""),
                }
            )
            entities.append(entity)

    entity_columns = BASE_ENTITY_COLUMNS + business_columns
    return entity_columns, entities


def validate_entity_ids(entities: list[dict[str, str]]) -> set[str]:
    ids = [entity["id"] for entity in entities]
    empty_ids = sum(not entity_id for entity_id in ids)
    duplicate_ids = sorted(
        entity_id for entity_id, count in Counter(ids).items() if entity_id and count > 1
    )
    if empty_ids or duplicate_ids:
        raise ValueError(
            f"Entity ID không hợp lệ: id rỗng={empty_ids}, id trùng={duplicate_ids}"
        )
    return set(ids)


def validate_relations(
    relations: list[dict[str, str]], entity_ids: set[str]
) -> list[tuple[int, str, str]]:
    orphans: list[tuple[int, str, str]] = []
    for row_number, relation in enumerate(relations, start=2):
        source_id = relation.get("source_id", "")
        target_id = relation.get("target_id", "")
        if source_id not in entity_ids:
            orphans.append((row_number, "source_id", source_id))
        if target_id not in entity_ids:
            orphans.append((row_number, "target_id", target_id))
    return orphans


def write_csv(
    path: Path, columns: list[str], rows: list[dict[str, str]]
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def print_counts(title: str, values: list[str]) -> None:
    print(title)
    for value, count in sorted(Counter(values).items()):
        print(f"  {value}: {count}")


def main() -> None:
    entity_columns, entities = build_entities()
    entity_ids = validate_entity_ids(entities)
    relation_columns, relations = read_csv(RELATION_SOURCE)
    orphans = validate_relations(relations, entity_ids)

    if orphans:
        print("Phát hiện orphan reference:")
        for row_number, column, value in orphans:
            print(f"  {RELATION_SOURCE} dòng {row_number}: {column}={value!r}")
        raise SystemExit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "entities.csv", entity_columns, entities)
    write_csv(OUTPUT_DIR / "relations.csv", relation_columns, relations)

    print_counts("Số entity theo type:", [entity["type"] for entity in entities])
    print_counts(
        "Số relation theo relationship_type:",
        [relation.get("relationship_type", "") for relation in relations],
    )
    print("Orphan reference: không có")
    print(f"Đã ghi {OUTPUT_DIR / 'entities.csv'}")
    print(f"Đã ghi {OUTPUT_DIR / 'relations.csv'}")


if __name__ == "__main__":
    main()