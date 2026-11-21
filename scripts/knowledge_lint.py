#!/usr/bin/env python3
"""Dependency-free structural and referential quality checks for CNC Knowledge."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

ENTITY_ID_RE = re.compile(
    r"^(KNOW|TERM|MTYPE|MACHINE|MINST|VENDOR|BRAND|PRODUCT|SUBSYS|PART|MAT|"
    r"PROCESS|TOOL|FIXTURE|SOFTWARE|ALGO|PROTO|INTERFACE|SIGNAL|PARAM|METRIC|"
    r"STD|TEST|MEAS|BOM|DOC|ASSET|PROC|FAULT|ALARM|CASE|APP)-[0-9]{6}$"
)
RELATION_ID_RE = re.compile(r"^REL-[0-9]{6}$")
SOURCE_ID_RE = re.compile(r"^SRC-[0-9]{6}$")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
CHAPTER_RE = re.compile(
    r"^\|\s*([0-9]{2})\s*\|\s*.*?docs/([0-9]{2}-[a-z0-9-]+)/",
    re.MULTILINE,
)
SOURCE_CITATION_RE = re.compile(r"SRC-[0-9]{6}")
MEDIA_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff",
    ".svg", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".odp",
}


class Reporter:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.counts: dict[str, int] = {}

    def error(self, message: str) -> None:
        self.errors.append(message)

    def count(self, name: str, value: int) -> None:
        self.counts[name] = value


def is_entity_id(value: object) -> bool:
    return isinstance(value, str) and ENTITY_ID_RE.fullmatch(value) is not None


def is_relation_id(value: object) -> bool:
    return isinstance(value, str) and RELATION_ID_RE.fullmatch(value) is not None


def is_source_id(value: object) -> bool:
    return isinstance(value, str) and SOURCE_ID_RE.fullmatch(value) is not None


def parse_markdown_links(content: str) -> list[str]:
    return [match.group(1) for match in LINK_RE.finditer(content)]


def resolve_internal_target(markdown_file: Path, target: str, repo_root: Path) -> Path | None:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    raw_path = unquote(parsed.path)
    candidate = (repo_root / raw_path.lstrip("/")) if raw_path.startswith("/") else (
        markdown_file.parent / raw_path
    )
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"link escapes repository root: {target}") from exc
    return resolved


def read_json(path: Path, reporter: Reporter) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        reporter.error(f"{path}: invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        reporter.error(f"{path}: JSON root must be an object")
        return None
    return value


def read_csv(path: Path, reporter: Reporter) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    except OSError as exc:
        reporter.error(f"{path}: cannot read CSV: {exc}")
        return []


def valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def valid_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def collect_records(directory: Path, id_field: str, validator, reporter: Reporter):
    records: dict[str, tuple[dict, Path]] = {}
    if not directory.is_dir():
        reporter.error(f"required directory missing: {directory}")
        return records
    for path in sorted(directory.rglob("*.json")):
        record = read_json(path, reporter)
        if record is None:
            continue
        record_id = record.get(id_field)
        if not validator(record_id):
            reporter.error(f"{path}: invalid {id_field}: {record_id!r}")
            continue
        if record_id in records:
            reporter.error(f"{path}: duplicate ID {record_id}")
            continue
        if path.stem != record_id:
            reporter.error(f"{path}: filename must equal {record_id}.json")
        records[record_id] = (record, path)
    return records


def check_repo(root: Path, reporter: Reporter) -> None:
    plan_path = root / "TaskPlan.md"
    if not plan_path.is_file():
        reporter.error("root TaskPlan.md is missing")
        return
    plan = plan_path.read_text(encoding="utf-8")
    if "main" not in plan or "resouces/" not in plan:
        reporter.error("root TaskPlan.md must include main and resouces rules")

    chapters: dict[str, str] = {}
    for chapter_id, slug in CHAPTER_RE.findall(plan):
        if chapter_id in chapters:
            reporter.error(f"duplicate chapter mapping: {chapter_id}")
        chapters[chapter_id] = slug
    if len(chapters) != 22:
        reporter.error(f"expected 22 chapter mappings, found {len(chapters)}")
    reporter.count("chapters", len(chapters))

    for chapter_id, slug in sorted(chapters.items()):
        required = (
            root / "docs" / slug / "README.md",
            root / "docs" / "TaskPlan" / slug / "TaskPlan.md",
            root / "resouces" / slug / "README.md",
        )
        for path in required:
            if not path.is_file():
                reporter.error(f"{chapter_id}: missing {path.relative_to(root)}")
        chapter_plan = root / "docs" / "TaskPlan" / slug / "TaskPlan.md"
        if chapter_plan.is_file():
            text = chapter_plan.read_text(encoding="utf-8")
            if re.search(r"^##\s+(Guide|Limit)\b", text, re.MULTILINE | re.IGNORECASE):
                reporter.error(f"{chapter_plan.relative_to(root)} must inherit root Guide/Limit")

    markdown_files = sorted(root.rglob("*.md"))
    internal_links = 0
    for path in markdown_files:
        if ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            reporter.error(f"{path}: cannot read: {exc}")
            continue
        for target in parse_markdown_links(text):
            try:
                resolved = resolve_internal_target(path, target, root)
            except ValueError as exc:
                reporter.error(f"{path.relative_to(root)}: {exc}")
                continue
            if resolved is not None:
                internal_links += 1
                if not resolved.exists():
                    reporter.error(f"{path.relative_to(root)}: broken local link: {target}")
    reporter.count("markdown_files", len(markdown_files))
    reporter.count("internal_links", internal_links)

    model = root / "docs" / "data-model"
    entity_schema = read_json(model / "entity.schema.json", reporter)
    relation_schema = read_json(model / "relationship.schema.json", reporter)
    source_schema = read_json(model / "source.schema.json", reporter)
    entity_rows = read_csv(model / "entity-types.csv", reporter)
    relation_rows = read_csv(model / "relation-types.csv", reporter)

    entity_map = {row.get("entity_type", ""): row.get("id_prefix", "") for row in entity_rows}
    if len(entity_map) != len(entity_rows):
        reporter.error("entity-types.csv has duplicate entity_type")
    entity_enum = entity_schema.get("properties", {}).get("entity_type", {}).get("enum", []) if entity_schema else []
    if set(entity_map) != set(entity_enum):
        reporter.error("entity-types.csv differs from entity.schema.json")

    relation_set = {row.get("predicate", "") for row in relation_rows}
    relation_enum = relation_schema.get("properties", {}).get("predicate", {}).get("enum", []) if relation_schema else []
    if len(relation_set) != len(relation_rows):
        reporter.error("relation-types.csv has duplicate predicates")
    if relation_set != set(relation_enum):
        reporter.error("relation-types.csv differs from relationship.schema.json")

    if source_schema:
        required_source = set(source_schema.get("required", []))
        for field in ("authority_tier", "evidence_kind", "rights_status"):
            if field not in required_source:
                reporter.error(f"source.schema.json must require {field}")

    reporter.count("entity_types", len(entity_map))
    reporter.count("relation_types", len(relation_set))

    entities = collect_records(
        root / "docs" / "data" / "entities", "entity_id", is_entity_id, reporter
    )
    relations = collect_records(
        root / "docs" / "data" / "relationships", "relation_id", is_relation_id, reporter
    )
    sources = collect_records(
        root / "docs" / "data" / "sources", "source_id", is_source_id, reporter
    )
    reporter.count("entity_records", len(entities))
    reporter.count("relationship_records", len(relations))
    reporter.count("source_records", len(sources))

    if entity_schema:
        required_fields = set(entity_schema.get("required", []))
        lifecycle = entity_schema.get("properties", {}).get("lifecycle_status", {}).get("enum", [])
        verification = entity_schema.get("properties", {}).get("verification_status", {}).get("enum", [])
        for entity_id, (record, path) in entities.items():
            missing = required_fields - set(record)
            if missing:
                reporter.error(f"{path.relative_to(root)}: missing {sorted(missing)}")
            prefix = entity_map.get(record.get("entity_type"))
            if prefix is None or entity_id.split("-", 1)[0] != prefix:
                reporter.error(f"{path.relative_to(root)}: ID prefix does not match entity_type")
            if path.parent.name != prefix:
                reporter.error(f"{path.relative_to(root)}: store record in prefix directory {prefix}/")
            if record.get("lifecycle_status") not in lifecycle:
                reporter.error(f"{path.relative_to(root)}: invalid lifecycle_status")
            if record.get("verification_status") not in verification:
                reporter.error(f"{path.relative_to(root)}: invalid verification_status")
            for field in ("created_at", "updated_at"):
                if not valid_datetime(record.get(field)):
                    reporter.error(f"{path.relative_to(root)}: {field} must be ISO 8601")
            if record.get("verified_at") is not None and not valid_datetime(record["verified_at"]):
                reporter.error(f"{path.relative_to(root)}: verified_at must be ISO 8601 or null")
            for source_id in record.get("source_ids", []):
                if not is_source_id(source_id) or source_id not in sources:
                    reporter.error(f"{path.relative_to(root)}: unresolved source ID {source_id}")
            if record.get("entity_type") == "asset_file":
                file_path = record.get("attributes", {}).get("file_path")
                asset_path = Path(file_path) if isinstance(file_path, str) else Path("/")
                if asset_path.is_absolute() or ".." in asset_path.parts or not asset_path.parts or asset_path.parts[0] != "resouces":
                    reporter.error(f"{path.relative_to(root)}: ASSET file_path must stay under resouces/")
                elif not (root / asset_path).is_file():
                    reporter.error(f"{path.relative_to(root)}: missing ASSET file {file_path}")

    if relation_schema:
        required_fields = set(relation_schema.get("required", []))
        for relation_id, (record, path) in relations.items():
            missing = required_fields - set(record)
            if missing:
                reporter.error(f"{path.relative_to(root)}: missing {sorted(missing)}")
            if record.get("predicate") not in relation_set:
                reporter.error(f"{path.relative_to(root)}: unknown predicate")
            for field in ("subject_id", "object_id"):
                target = record.get(field)
                if not is_entity_id(target) or target not in entities:
                    reporter.error(f"{path.relative_to(root)}: unresolved {field} {target!r}")
            for source_id in record.get("source_ids", []):
                if not is_source_id(source_id) or source_id not in sources:
                    reporter.error(f"{path.relative_to(root)}: unresolved source ID {source_id}")

    if source_schema:
        required_fields = set(source_schema.get("required", []))
        properties = source_schema.get("properties", {})
        for source_id, (record, path) in sources.items():
            missing = required_fields - set(record)
            if missing:
                reporter.error(f"{path.relative_to(root)}: missing {sorted(missing)}")
            for field in ("source_type", "rights_status", "authority_tier", "evidence_kind"):
                allowed = properties.get(field, {}).get("enum", [])
                if record.get(field) not in allowed:
                    reporter.error(f"{path.relative_to(root)}: invalid {field}")
            if not valid_date(record.get("accessed_on")):
                reporter.error(f"{path.relative_to(root)}: accessed_on must be YYYY-MM-DD")

    citations = 0
    for slug in chapters.values():
        chapter_dir = root / "docs" / slug
        if chapter_dir.is_dir():
            for path in chapter_dir.rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                for source_id in SOURCE_CITATION_RE.findall(text):
                    citations += 1
                    if source_id not in sources:
                        reporter.error(f"{path.relative_to(root)}: unknown citation {source_id}")
    reporter.count("chapter_source_citations", citations)

    resource_root = root / "resouces"
    if not resource_root.is_dir():
        reporter.error("resouces directory is missing")
    else:
        known = set(chapters.values())
        for child in resource_root.iterdir():
            if child.is_file() and child.name != "README.md":
                reporter.error(f"resource must be inside a chapter directory: {child.relative_to(root)}")
            if child.is_dir() and child.name not in known:
                reporter.error(f"unknown resource chapter directory: {child.relative_to(root)}")
        for slug in known:
            if not (resource_root / slug / "README.md").is_file():
                reporter.error(f"missing resource README: resouces/{slug}/README.md")

    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "resouces" in path.parts:
            continue
        relative = path.relative_to(root)
        if "docs" not in relative.parts:
            continue
        suffix = path.suffix.lower()
        if suffix in MEDIA_EXTENSIONS:
            reporter.error(f"media/document file must be under resouces/: {relative}")
        elif suffix == ".csv" and len(relative.parts) > 2 and relative.parts[1] not in {
            "data-model", "templates", "coverage", "data"
        }:
            reporter.error(f"chapter knowledge CSV must be under resouces/: {relative}")

    coverage_rows = read_csv(root / "docs" / "coverage" / "CHAPTER-COVERAGE.csv", reporter)
    coverage_ids = [row.get("chapter_id", "") for row in coverage_rows]
    if set(coverage_ids) != set(chapters) or len(coverage_ids) != len(chapters):
        reporter.error("coverage matrix must contain exactly one row for each chapter")
    for row in coverage_rows:
        try:
            level = int(row.get("coverage_level", "-1"))
        except ValueError:
            level = -1
        if level not in range(6):
            reporter.error(f"invalid coverage_level for {row.get('chapter_id')}")
        if level == 0 and row.get("coverage_label") != "not_started":
            reporter.error(f"level 0 must use not_started for {row.get('chapter_id')}")
        for field in (
            "knowledge_articles", "verified_entities", "verified_relationships",
            "source_records", "asset_records",
        ):
            try:
                if int(row.get(field, "-1")) < 0:
                    raise ValueError
            except ValueError:
                reporter.error(f"invalid {field} for {row.get('chapter_id')}")
    reporter.count("coverage_rows", len(coverage_rows))


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint CNC Knowledge structure and data.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    reporter = Reporter()
    check_repo(args.root.resolve(), reporter)
    for name, value in sorted(reporter.counts.items()):
        print(f"{name}: {value}")
    for error in reporter.errors:
        print(f"ERROR: {error}")
    print(f"RESULT: {'PASS' if not reporter.errors else 'FAIL'} ({len(reporter.errors)} errors)")
    return 0 if not reporter.errors else 1


if __name__ == "__main__":
    sys.exit(main())
