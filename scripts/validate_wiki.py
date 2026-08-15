"""Validate the generated Wiki Risk Graph and write a Markdown report."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
WIKI_DIR = PROJECT_ROOT / "wiki"
REPORT_PATH = OUTPUT_DIR / "wiki_validation_report.md"

WIKILINK_PATTERN = re.compile(r"\[\[([^|\]#]+)(?:#[^|\]]+)?(?:\|[^\]]+)?\]\]")
FRONTMATTER_PATTERN = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)


@dataclass
class ValidationResult:
    markdown_files: int = 0
    wikilinks: int = 0
    broken_links: list[str] = field(default_factory=list)
    duplicate_entity_ids: list[str] = field(default_factory=list)
    unknown_page_ids: list[str] = field(default_factory=list)
    duplicate_page_ids: list[str] = field(default_factory=list)
    missing_entity_pages: list[str] = field(default_factory=list)
    relation_orphans: list[str] = field(default_factory=list)
    risks_without_controls: list[str] = field(default_factory=list)
    risks_without_events: list[str] = field(default_factory=list)
    orphan_pages: list[str] = field(default_factory=list)

    @property
    def data_errors(self) -> list[str]:
        return (
            self.duplicate_entity_ids
            + self.relation_orphans
            + self.risks_without_controls
            + self.risks_without_events
        )

    @property
    def program_errors(self) -> list[str]:
        return (
            self.broken_links
            + self.unknown_page_ids
            + self.duplicate_page_ids
            + self.missing_entity_pages
            + self.orphan_pages
        )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def parse_frontmatter(content: str) -> dict[str, str]:
    match = FRONTMATTER_PATTERN.match(content)
    if match is None:
        return {}

    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        raw_value = raw_value.strip()
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value.strip("'\"")
        values[key.strip()] = str(value)
    return values


def page_key(path: Path) -> str:
    return path.relative_to(WIKI_DIR).with_suffix("").as_posix().casefold()


def validate() -> ValidationResult:
    result = ValidationResult()
    entities = read_csv(OUTPUT_DIR / "entities.csv")
    relations = read_csv(OUTPUT_DIR / "relations.csv")
    pages = sorted(WIKI_DIR.rglob("*.md"))
    result.markdown_files = len(pages)

    entity_id_counts = Counter(entity.get("id", "") for entity in entities)
    result.duplicate_entity_ids = sorted(
        entity_id for entity_id, count in entity_id_counts.items() if entity_id and count > 1
    )
    entity_ids = {entity_id for entity_id in entity_id_counts if entity_id}
    entities_by_id = {
        entity["id"]: entity
        for entity in entities
        if entity.get("id") and entity_id_counts[entity["id"]] == 1
    }

    available_pages = {page_key(page) for page in pages}
    page_ids: list[str] = []
    for page in pages:
        content = page.read_text(encoding="utf-8")
        links = WIKILINK_PATTERN.findall(content)
        result.wikilinks += len(links)
        relative_page = page.relative_to(WIKI_DIR).as_posix()

        if not links:
            result.orphan_pages.append(relative_page)
        for target in links:
            normalized_target = target.strip().replace("\\", "/").removesuffix(".md").casefold()
            if normalized_target not in available_pages:
                result.broken_links.append(f"{relative_page} -> {target}")

        frontmatter = parse_frontmatter(content)
        page_id = frontmatter.get("id", "")
        if page_id:
            page_ids.append(page_id)
            if page_id not in entity_ids:
                result.unknown_page_ids.append(f"{relative_page}: {page_id}")

    page_id_counts = Counter(page_ids)
    result.duplicate_page_ids = sorted(
        page_id for page_id, count in page_id_counts.items() if count > 1
    )
    result.missing_entity_pages = sorted(entity_ids - set(page_ids))

    controls_by_risk: dict[str, set[str]] = defaultdict(set)
    events_by_risk: dict[str, set[str]] = defaultdict(set)
    for row_number, relation in enumerate(relations, start=2):
        source_id = relation.get("source_id", "")
        target_id = relation.get("target_id", "")
        missing = []
        if source_id not in entity_ids:
            missing.append(f"source_id={source_id!r}")
        if target_id not in entity_ids:
            missing.append(f"target_id={target_id!r}")
        if missing:
            result.relation_orphans.append(
                f"relations.csv dòng {row_number}: {', '.join(missing)}"
            )
            continue

        relationship_type = relation.get("relationship_type", "")
        if relationship_type == "MITIGATES":
            controls_by_risk[target_id].add(source_id)
        elif relationship_type == "OBSERVED_AS":
            events_by_risk[source_id].add(target_id)

    risk_ids = sorted(
        entity_id
        for entity_id, entity in entities_by_id.items()
        if entity.get("type") == "RuiRo"
    )
    result.risks_without_controls = [
        risk_id for risk_id in risk_ids if not controls_by_risk[risk_id]
    ]
    result.risks_without_events = [
        risk_id for risk_id in risk_ids if not events_by_risk[risk_id]
    ]
    return result


def display_items(items: list[str]) -> str:
    if not items:
        return "Không có."
    return "\n".join(f"- `{item}`" for item in items)


def build_report(result: ValidationResult) -> str:
    status = "ĐẠT" if not result.data_errors and not result.program_errors else "CHƯA ĐẠT"
    lines = [
        "# Báo cáo kiểm thử Wiki Risk Graph",
        "",
        f"**Kết quả tổng thể:** {status}",
        "",
        "## Thống kê",
        "",
        f"- Tổng số file Markdown: **{result.markdown_files}**",
        f"- Tổng số wikilink: **{result.wikilinks}**",
        f"- Wikilink trỏ tới trang không tồn tại: **{len(result.broken_links)}**",
        f"- Entity bị trùng ID: **{len(result.duplicate_entity_ids)}**",
        f"- Trang có ID không tồn tại trong entities.csv: **{len(result.unknown_page_ids)}**",
        f"- ID bị trùng giữa các trang: **{len(result.duplicate_page_ids)}**",
        f"- Entity chưa có trang Wiki: **{len(result.missing_entity_pages)}**",
        f"- Relation có source hoặc target không tồn tại: **{len(result.relation_orphans)}**",
        f"- RuiRo không có KiemSoat: **{len(result.risks_without_controls)}**",
        f"- RuiRo không có SuKienRuiRo: **{len(result.risks_without_events)}**",
        f"- Trang không có liên kết với trang khác: **{len(result.orphan_pages)}**",
        "",
        "## Lỗi dữ liệu",
        "",
        "### Entity bị trùng ID",
        "",
        display_items(result.duplicate_entity_ids),
        "",
        "### Relation có tham chiếu không tồn tại",
        "",
        display_items(result.relation_orphans),
        "",
        "### RuiRo không có KiemSoat",
        "",
        display_items(result.risks_without_controls),
        "",
        "### RuiRo không có SuKienRuiRo",
        "",
        display_items(result.risks_without_events),
        "",
        "## Lỗi chương trình sinh Wiki",
        "",
        "### Wikilink bị hỏng",
        "",
        display_items(result.broken_links),
        "",
        "### Trang có ID ngoài entities.csv",
        "",
        display_items(result.unknown_page_ids),
        "",
        "### ID bị trùng giữa các trang",
        "",
        display_items(result.duplicate_page_ids),
        "",
        "### Entity chưa có trang Wiki",
        "",
        display_items(result.missing_entity_pages),
        "",
        "### Trang không có liên kết với trang khác",
        "",
        display_items(result.orphan_pages),
        "",
        "## Kết luận",
        "",
    ]
    if status == "ĐẠT":
        lines.append("Không phát hiện lỗi dữ liệu hoặc lỗi chương trình theo các tiêu chí kiểm thử.")
    else:
        lines.append(
            f"Phát hiện {len(result.data_errors)} lỗi dữ liệu và "
            f"{len(result.program_errors)} lỗi chương trình. Không có quan hệ nào được tự sinh để che lỗi."
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    result = validate()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(result), encoding="utf-8")

    print(f"Tổng số file Markdown: {result.markdown_files}")
    print(f"Tổng số wikilink: {result.wikilinks}")
    print(f"Lỗi dữ liệu: {len(result.data_errors)}")
    print(f"Lỗi chương trình: {len(result.program_errors)}")
    print(f"Đã ghi báo cáo: {REPORT_PATH}")
    if result.data_errors or result.program_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()