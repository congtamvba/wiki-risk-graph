"""Load normalized Wiki Risk Graph CSV files into Neo4j."""

from __future__ import annotations

import csv
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
SCHEMA_PATH = PROJECT_ROOT / "cypher" / "schema.cypher"

NODE_TYPES = {"RuiRo", "KiemSoat", "SuKienRuiRo"}
RELATION_ENDPOINTS = {
    "MITIGATES": ("KiemSoat", "RuiRo"),
    "OBSERVED_AS": ("RuiRo", "SuKienRuiRo"),
}
REQUIRED_ENV = ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "NEO4J_DATABASE")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def properties_without_empty_values(row: dict[str, str], *excluded: str) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in excluded and value not in (None, "")
    }


def validate_input(
    entities: list[dict[str, str]], relations: list[dict[str, str]]
) -> dict[str, dict[str, str]]:
    entity_ids = [entity.get("id", "") for entity in entities]
    duplicate_ids = sorted(
        entity_id
        for entity_id, count in Counter(entity_ids).items()
        if entity_id and count > 1
    )
    if "" in entity_ids or duplicate_ids:
        raise ValueError(f"Entity ID rỗng hoặc trùng: {duplicate_ids}")

    entities_by_id = {entity["id"]: entity for entity in entities}
    unknown_types = sorted({entity.get("type", "") for entity in entities} - NODE_TYPES)
    if unknown_types:
        raise ValueError(f"Entity type không được hỗ trợ: {unknown_types}")

    for row_number, relation in enumerate(relations, start=2):
        source = entities_by_id.get(relation.get("source_id", ""))
        target = entities_by_id.get(relation.get("target_id", ""))
        if source is None or target is None:
            raise ValueError(f"Orphan reference tại relations.csv dòng {row_number}")
        relationship_type = relation.get("relationship_type", "")
        expected = RELATION_ENDPOINTS.get(relationship_type)
        actual = (source["type"], target["type"])
        if expected is None or actual != expected:
            raise ValueError(
                f"Quan hệ không hợp lệ tại dòng {row_number}: "
                f"{actual[0]} -{relationship_type}-> {actual[1]}"
            )
    return entities_by_id


def schema_statements() -> list[str]:
    lines = [
        line for line in SCHEMA_PATH.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("//")
    ]
    return [statement.strip() for statement in "\n".join(lines).split(";") if statement.strip()]


def create_schema(session: Any) -> None:
    for statement in schema_statements():
        session.run(statement).consume()


def load_nodes(session: Any, entities: list[dict[str, str]]) -> None:
    rows_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entity in entities:
        rows_by_type[entity["type"]].append(
            {
                "id": entity["id"],
                "properties": properties_without_empty_values(entity, "id", "type"),
            }
        )

    for node_type, rows in rows_by_type.items():
        if node_type not in NODE_TYPES:
            raise ValueError(f"Node type không được hỗ trợ: {node_type}")
        query = (
            f"UNWIND $rows AS row "
            f"MERGE (node:{node_type} {{id: row.id}}) "
            "SET node += row.properties"
        )
        session.run(query, rows=rows).consume()


def load_relations(
    session: Any,
    relations: list[dict[str, str]],
    entities_by_id: dict[str, dict[str, str]],
) -> None:
    rows_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for relation in relations:
        rows_by_type[relation["relationship_type"]].append(
            {
                "source_id": relation["source_id"],
                "target_id": relation["target_id"],
                "properties": properties_without_empty_values(
                    relation, "source_id", "relationship_type", "target_id"
                ),
            }
        )

    for relationship_type, rows in rows_by_type.items():
        source_type, target_type = RELATION_ENDPOINTS[relationship_type]
        query = (
            f"UNWIND $rows AS row "
            f"MATCH (source:{source_type} {{id: row.source_id}}) "
            f"MATCH (target:{target_type} {{id: row.target_id}}) "
            f"MERGE (source)-[relationship:{relationship_type}]->(target) "
            "SET relationship += row.properties"
        )
        session.run(query, rows=rows).consume()


def require_configuration() -> dict[str, str]:
    load_dotenv(PROJECT_ROOT / ".env")
    config = {name: os.getenv(name, "").strip() for name in REQUIRED_ENV}
    missing = [name for name, value in config.items() if not value]
    if missing:
        raise ValueError(f"Thiếu cấu hình trong .env: {', '.join(missing)}")
    return config


def main() -> None:
    try:
        config = require_configuration()
        entities = read_csv(OUTPUT_DIR / "entities.csv")
        relations = read_csv(OUTPUT_DIR / "relations.csv")
        entities_by_id = validate_input(entities, relations)

        with GraphDatabase.driver(
            config["NEO4J_URI"],
            auth=(config["NEO4J_USER"], config["NEO4J_PASSWORD"]),
        ) as driver:
            driver.verify_connectivity()
            with driver.session(database=config["NEO4J_DATABASE"]) as session:
                create_schema(session)
                load_nodes(session, entities)
                load_relations(session, relations, entities_by_id)

        print(f"Đã nạp {len(entities)} node và {len(relations)} relation vào Neo4j.")
        print("MERGE bảo đảm chạy lại không tạo duplicate theo cùng ID/cặp endpoint.")
    except (ServiceUnavailable, Neo4jError) as error:
        print("Không thể kết nối hoặc thực thi trên Neo4j.", file=sys.stderr)
        print(
            "Hãy mở Neo4j Desktop, khởi động DBMS, kiểm tra tên database và các biến "
            "NEO4J_* trong .env, rồi chạy lại script.",
            file=sys.stderr,
        )
        print(f"Chi tiết: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except (FileNotFoundError, ValueError) as error:
        print(f"Dữ liệu hoặc cấu hình không hợp lệ: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()