from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "skills.yaml"
COMPARE_GROUPS = ["前任.skill", "自己.skill", "老板.skill", "导师.skill", "父母.skill", "偶像陪伴"]

REQUIRED_FIELDS = [
    "id",
    "name",
    "repo",
    "url",
    "category",
    "summary",
    "focus_object",
    "scene_tags",
    "source_types",
    "privacy_level",
    "risk_tags",
    "skill_md_verified",
    "skill_md_location",
    "install_difficulty",
    "beginner_friendly",
    "last_pushed_at",
    "active_bucket",
    "scores",
    "compare_group",
    "compare_note",
    "audit",
]


def load_catalog() -> dict:
    with CATALOG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def active_bucket(last_pushed_at: str, audited_at: str) -> str:
    pushed_date = dt.date.fromisoformat(last_pushed_at)
    audited_date = dt.date.fromisoformat(audited_at)
    delta = (audited_date - pushed_date).days
    if delta <= 30:
        return "30天内活跃"
    if delta <= 90:
        return "90天内活跃"
    if delta <= 180:
        return "180天内活跃"
    return "180天以上"


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    catalog = load_catalog()
    meta = catalog.get("meta", {})
    vocab = catalog.get("vocab", {})
    skills = catalog.get("skills", [])
    if meta.get("total_skills") != len(skills):
        fail(f"meta.total_skills={meta.get('total_skills')} does not match skills count={len(skills)}")
    seen_ids = set()
    seen_repos = set()
    seen_urls = set()
    compare_counts = {group: 0 for group in COMPARE_GROUPS}
    for index, skill in enumerate(skills, start=1):
        for field in REQUIRED_FIELDS:
            if field not in skill:
                fail(f"Skill #{index} missing field: {field}")
        if skill["id"] in seen_ids:
            fail(f"Duplicate id: {skill['id']}")
        seen_ids.add(skill["id"])
        if skill["repo"] in seen_repos:
            fail(f"Duplicate repo: {skill['repo']}")
        seen_repos.add(skill["repo"])
        if skill["url"] in seen_urls:
            fail(f"Duplicate url: {skill['url']}")
        seen_urls.add(skill["url"])
        if not skill["scene_tags"] or any(item not in vocab["scene_tags"] for item in skill["scene_tags"]):
            fail(f"Invalid scene_tags for {skill['repo']}")
        if not skill["source_types"] or any(item not in vocab["source_types"] for item in skill["source_types"]):
            fail(f"Invalid source_types for {skill['repo']}")
        if not skill["risk_tags"] or any(item not in vocab["risk_tags"] for item in skill["risk_tags"]):
            fail(f"Invalid risk_tags for {skill['repo']}")
        if skill["privacy_level"] not in vocab["privacy_levels"]:
            fail(f"Invalid privacy_level for {skill['repo']}")
        if skill["install_difficulty"] not in vocab["install_difficulties"]:
            fail(f"Invalid install_difficulty for {skill['repo']}")
        if skill["active_bucket"] not in vocab["active_buckets"]:
            fail(f"Invalid active_bucket for {skill['repo']}")
        if len(skill["audit"]["inspected_files"]) < 2:
            fail(f"Inspected files not enough for {skill['repo']}")
        if not skill["audit"]["readme_checked"]:
            fail(f"README not checked for {skill['repo']}")
        if not skill["audit"]["evidence_summary"]:
            fail(f"Evidence summary missing for {skill['repo']}")
        if skill["skill_md_verified"] and skill["skill_md_location"] not in {"root", "subdir"}:
            fail(f"Invalid skill_md_location for verified repo {skill['repo']}")
        if not skill["skill_md_verified"] and skill["skill_md_location"] != "none":
            fail(f"Non-verified repo {skill['repo']} must use skill_md_location=none")
        expected_bucket = active_bucket(skill["last_pushed_at"], meta["audited_at"])
        if skill["active_bucket"] != expected_bucket:
            fail(f"Active bucket mismatch for {skill['repo']}: {skill['active_bucket']} vs {expected_bucket}")
        for metric in ("usability", "completeness", "maintenance", "privacy_friendliness"):
            value = skill["scores"].get(metric)
            if not isinstance(value, int) or not 1 <= value <= 5:
                fail(f"Invalid score {metric} for {skill['repo']}")
        for group in skill["compare_group"]:
            if group not in COMPARE_GROUPS:
                fail(f"Invalid compare_group for {skill['repo']}: {group}")
            compare_counts[group] += 1
        if skill["compare_group"] and not skill["compare_note"]:
            fail(f"compare_note missing for {skill['repo']}")
    for group, count in compare_counts.items():
        if count < 2:
            fail(f"Compare group {group} needs at least 2 items, got {count}")
    print(f"Validated {len(skills)} skills from {CATALOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
