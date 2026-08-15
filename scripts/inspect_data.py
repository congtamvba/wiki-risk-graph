"""Inspect the seed CSV files used by the Wiki Risk Graph lab."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

FILES = {
    "risk_profiles_seed.csv": "RuiRo",
    "controls_seed.csv": "KiemSoat",
    "risk_events_seed.csv": "SuKienRuiRo",
    "relationships_seed.csv": "edge",
}


def read_csv(filename: str) -> tuple[list[str], list[dict[str, str]]]:
    """Return the header and rows from a seed CSV."""
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError(f"CSV không có dòng tiêu đề: {path}")
        return list(reader.fieldnames), list(reader)


def null_counts(columns: list[str], rows: list[dict[str, str]]) -> dict[str, int]:
    return {
        column: sum(not (row.get(column) or "").strip() for row in rows)
        for column in columns
    }


def duplicate_report(columns: list[str], rows: list[dict[str, str]]) -> dict[str, Any]:
    row_counts = Counter(tuple(row.get(column, "") for column in columns) for row in rows)
    duplicate_rows = sum(count - 1 for count in row_counts.values() if count > 1)

    id_counts = Counter(row.get("id", "") for row in rows) if "id" in columns else Counter()
    duplicate_ids = {
        value: count for value, count in id_counts.items() if value and count > 1
    }
    return {"duplicate_rows": duplicate_rows, "duplicate_ids": duplicate_ids}


def print_table_report(
    filename: str, node_label: str, columns: list[str], rows: list[dict[str, str]]
) -> None:
    duplicates = duplicate_report(columns, rows)
    non_nulls = {column: count for column, count in null_counts(columns, rows).items() if count}

    print(f"\n[{filename}]")
    print(f"  loại: {node_label}")
    print(f"  số dòng: {len(rows)}")
    print(f"  cột: {', '.join(columns)}")
    print(f"  khóa chính: {('id' if 'id' in columns else 'không có cột id')}")
    print(f"  null/rỗng: {non_nulls or 'không có'}")
    print(f"  duplicate dòng: {duplicates['duplicate_rows']}")
    print(f"  duplicate khóa chính: {duplicates['duplicate_ids'] or 'không có'}")


def report_missing_references(
    description: str,
    references: list[tuple[str, str]],
    known_ids: dict[str, set[str]],
) -> None:
    missing = [
        (source_id, target_id)
        for source_id, target_id in references
        if target_id not in known_ids.get("all", set())
    ]
    print(f"  {description}: {missing or 'không có'}")


def main() -> None:
    datasets: dict[str, tuple[list[str], list[dict[str, str]]]] = {
        filename: read_csv(filename) for filename in FILES
    }

    for filename, node_label in FILES.items():
        columns, rows = datasets[filename]
        print_table_report(filename, node_label, columns, rows)

    risk_ids = {row["id"] for row in datasets["risk_profiles_seed.csv"][1] if row.get("id")}
    control_ids = {row["id"] for row in datasets["controls_seed.csv"][1] if row.get("id")}
    event_ids = {row["id"] for row in datasets["risk_events_seed.csv"][1] if row.get("id")}

    event_rows = datasets["risk_events_seed.csv"][1]
    event_risk_refs = [(row.get("id", ""), row.get("risk_id", "")) for row in event_rows]
    print("\n[Khóa tham chiếu]")
    report_missing_references("risk_events_seed.csv.risk_id -> risk_profiles_seed.csv.id", event_risk_refs, {"all": risk_ids})

    control_rows = datasets["controls_seed.csv"][1]
    risk_rows = datasets["risk_profiles_seed.csv"][1]
    owner_unit_ids = {row.get("owner_unit_id", "") for row in risk_rows if row.get("owner_unit_id")}
    owner_role_ids = {row.get("owner_role_id", "") for row in control_rows if row.get("owner_role_id")}
    print(f"  owner_unit_id: {sorted(owner_unit_ids)} -> chưa có bảng master Đơn vị")
    print(f"  owner_role_id: {sorted(owner_role_ids)} -> chưa có bảng master Vai trò")

    relationship_columns, relationship_rows = datasets["relationships_seed.csv"]
    relationship_types = Counter(row.get("relationship_type", "") for row in relationship_rows)
    print("\n[Quan hệ]")
    print(f"  relationship_type: {dict(sorted(relationship_types.items()))}")
    print("  khóa tham chiếu bị thiếu:")
    relationship_reference_sets = {
        "MITIGATES": (control_ids, risk_ids),
        "OBSERVED_AS": (risk_ids, event_ids),
    }
    for relationship_type, (source_ids, target_ids) in relationship_reference_sets.items():
        typed_rows = [
            row for row in relationship_rows
            if row.get("relationship_type") == relationship_type
        ]
        missing_sources = sorted({row.get("source_id", "") for row in typed_rows} - source_ids)
        missing_targets = sorted({row.get("target_id", "") for row in typed_rows} - target_ids)
        print(
            f"    {relationship_type}: source_id={missing_sources or 'không có'}, "
            f"target_id={missing_targets or 'không có'}"
        )

    print("\n[MVP Wiki Risk Graph]")
    print("  node: RuiRo, KiemSoat, SuKienRuiRo")
    print("  edge: (KiemSoat)-[:MITIGATES]->(RuiRo)")
    print("        (RuiRo)-[:OBSERVED_AS]->(SuKienRuiRo)")
    print("  chưa có dữ liệu: Đơn vị, Vai trò, VanBan, DieuKhoan, QuyTrinh, BangChung")
    print("  lưu ý: mọi bản ghi hiện có data_origin=SYNTHETIC; VERIFIED chỉ có nghĩa trong phạm vi bài lab.")


if __name__ == "__main__":
    main()