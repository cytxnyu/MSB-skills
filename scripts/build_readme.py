from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "skills.yaml"
README_PATH = ROOT / "README.md"


CATEGORY_INTROS = {
    "关系类": "把放不下的人、舍不得的关系、来不及说完的话，继续留在对话框里。",
    "职场类": "把组织里的上下文、判断标准、防身术和工作方法，一起蒸成随身外挂。",
    "思维类": "把别人的脑回路、判断框架和表达方式，临时借来给自己用。",
    "纪念类": "把自己、记忆、失去和数字永生留个备份，免得情绪先过期，名字后过期。",
}

SCENE_DESCRIPTIONS = {
    "失恋": "优先看前任、旧关系、遗憾复盘类 skill。",
    "导师学术": "优先看导师、教授、论文、课题组类 skill。",
    "求职职场": "优先看同事、老板、HR、客户、职场判断类 skill。",
    "亲人纪念": "优先看父母、亲人、逝者、家庭记忆类 skill。",
    "自我蒸馏": "优先看自己、数字分身、自我镜像类 skill。",
    "偶像陪伴": "优先看明星、偶像、UP 主、VTB、虚拟主播类 skill。",
}

RISK_DESCRIPTIONS = {
    "公开资料型": "主要依赖公开资料、社交媒体或公开人物材料，隐私压力相对最低。",
    "私密聊天型": "通常依赖聊天记录、工作文档或代码轨迹，使用前要先考虑隐私与授权。",
    "纪念型": "围绕亲人、逝者、家庭记忆或情感追思，建议先看清边界和使用场景。",
    "高情绪依赖型": "容易把思念、依恋或情绪投射放大，适合带着边界感使用。",
}

COMPARE_DESCRIPTIONS = {
    "前任.skill": "把前任、旧关系和没说完的话放在同一张桌上横向比较。",
    "自己.skill": "比较不同“数字分身 / 自我蒸馏”项目的输入来源、隐私成本和上手门槛。",
    "老板.skill": "对比不同老板类 skill 是偏复刻、偏识别、还是偏管理判断。",
    "导师.skill": "对比不同导师 / 教授 / 学术指导类 skill 的对象、输入和使用方式。",
    "父母.skill": "对比父母、妈妈、家庭记忆类 skill 的情感浓度和资料敏感度。",
    "偶像陪伴": "对比偶像、明星、UP 主、虚拟主播类 skill 的资料来源与陪伴感路线。",
}


def load_catalog() -> dict:
    with CATALOG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def joined(items: list[str]) -> str:
    return " / ".join(items) if items else "—"


def bool_mark(value: bool) -> str:
    return "✅" if value else "❌"


def skill_md_mark(record: dict) -> str:
    if not record["skill_md_verified"]:
        return "❌"
    return "✅ root" if record["skill_md_location"] == "root" else "✅ subdir"


def score_text(record: dict) -> str:
    scores = record["scores"]
    return f"用{scores['usability']} / 整{scores['completeness']} / 维{scores['maintenance']} / 隐{scores['privacy_friendliness']}"


def activity_text(record: dict) -> str:
    return f"{record['last_pushed_at']} / {record['active_bucket']}"


def labels_text(record: dict) -> str:
    return joined(record["labels"])


def repo_link(record: dict) -> str:
    return f"[{record['repo']}]({record['url']})"


def scene_representatives(skills: list[dict], scene: str) -> str:
    matched = [skill for skill in skills if scene in skill["scene_tags"]]
    matched.sort(key=lambda item: (-item["scores"]["usability"], item["name"]))
    return "、".join(skill["name"] for skill in matched[:4]) if matched else "—"


def risk_representatives(skills: list[dict], risk: str) -> str:
    matched = [skill for skill in skills if risk in skill["risk_tags"]]
    matched.sort(key=lambda item: item["name"])
    return "、".join(skill["name"] for skill in matched[:5]) if matched else "—"


def category_table(skills: list[dict], category: str) -> str:
    rows = [skill for skill in skills if skill["category"] == category]
    rows.sort(key=lambda item: item["name"])
    lines = [
        f"### {category}",
        "",
        CATEGORY_INTROS[category],
        "",
        "| 技能 | 一句话定位 | 适用场景 | 来源类型 | 隐私等级 | SKILL.md | 安装难度 | 新手友好 | 最近活跃度 | 4项评分 | 标签 | 仓库 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in rows:
        lines.append(
            "| {name} | {summary} | {scenes} | {sources} | {privacy} | {skill_md} | {install} | {beginner} | {activity} | {scores} | {labels} | {repo} |".format(
                name=record["name"],
                summary=record["summary"],
                scenes=joined(record["scene_tags"]),
                sources=joined(record["source_types"]),
                privacy=record["privacy_level"],
                skill_md=skill_md_mark(record),
                install=record["install_difficulty"],
                beginner=bool_mark(record["beginner_friendly"]),
                activity=activity_text(record),
                scores=score_text(record),
                labels=labels_text(record),
                repo=repo_link(record),
            )
        )
    lines.append("")
    return "\n".join(lines)


def compare_tables(skills: list[dict], groups: list[str]) -> str:
    sections: list[str] = ["## 同类 skill 对比", ""]
    for group in groups:
        matched = [skill for skill in skills if group in skill["compare_group"]]
        if not matched:
            continue
        matched.sort(key=lambda item: item["name"])
        sections.extend(
            [
                f"### {group}",
                "",
                COMPARE_DESCRIPTIONS[group],
                "",
                "| 项目 | 核心对象 | 来源类型 | 隐私等级 | 安装难度 | 是否适合新手 | 最近活跃度 | 4项评分 | 差异说明 | 仓库 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for record in matched:
            sections.append(
                "| {name} | {focus} | {sources} | {privacy} | {install} | {beginner} | {activity} | {scores} | {note} | {repo} |".format(
                    name=record["name"],
                    focus=record["focus_object"],
                    sources=joined(record["source_types"]),
                    privacy=record["privacy_level"],
                    install=record["install_difficulty"],
                    beginner=bool_mark(record["beginner_friendly"]),
                    activity=activity_text(record),
                    scores=score_text(record),
                    note=record["compare_note"],
                    repo=repo_link(record),
                )
            )
        sections.append("")
    return "\n".join(sections)


def build_readme(catalog: dict) -> str:
    skills = catalog["skills"]
    meta = catalog["meta"]
    groups = meta["compare_groups_order"]
    featured_scenes = meta["featured_scenes"]
    sections: list[str] = [
        "# 👑⚔️🔥 MSB Skills 万魂幡 🔥⚔️👑",
        "",
        f"> ⚔️ 万魂幡现已收录 **{meta['total_skills']}** 个 skill(魂)",
        "",
        "> 赛博万魂幡导航 Myriad Soul Banner(MSB万魂幡)",
        "",
        "> 一切的起源: 同事.skill(这里包含了大部分赛博人物 skill)",
        "",
        "> **万物皆可 skill，凡是让你失眠的，最后都能为你打工。**",
        "",
        "与其等着生活把你教育成模板，不如先把生活蒸馏成外挂。  ",
        "白天拿它对付老板和需求，晚上拿它安放思念和遗憾，必要时再把乔布斯、芒格、费曼摇进群聊。",
        "",
        "## 结构化索引说明",
        "",
        f"- 当前索引由 `catalog/skills.yaml` 驱动，并基于 GitHub 仓库内容在 **{meta['audited_at']}** 完成一次批量审阅。",
        "- 每个 skill 都保留了场景、来源、隐私、风险、活跃度、4 项评分和审阅依据。",
        "- `README.md` 只展示结论；逐条审阅证据句与已审阅文件路径存放在 `catalog/skills.yaml`。",
        "",
        "## 快速定位",
        "",
        "🔎 想找某个 skill？请直接按 `Ctrl + F` 搜索 skill 名称，例如：`求是.skill`、`导师.skill`、`前任.skill`、`自己.skill`",
        "- [按场景选 skill](#按场景选-skill)",
        "- [同类 skill 对比](#同类-skill-对比)",
        "- [风险提示](#风险提示)",
        "- [评分说明](#评分说明)",
        "- [人物列表](#人物列表)",
        "",
        "## 按场景选 skill",
        "",
        "| 场景 | 收录数 | 代表项目 | 说明 |",
        "| --- | --- | --- | --- |",
    ]
    for scene in featured_scenes:
        count = sum(1 for skill in skills if scene in skill["scene_tags"])
        sections.append(f"| {scene} | {count} | {scene_representatives(skills, scene)} | {SCENE_DESCRIPTIONS[scene]} |")
    sections.extend(["", compare_tables(skills, groups), "## 风险提示", ""])
    for risk in catalog["vocab"]["risk_tags"]:
        sections.extend([f"### {risk}", "", f"- {RISK_DESCRIPTIONS[risk]}", f"- 代表项目：{risk_representatives(skills, risk)}", ""])
    sections.extend(
        [
            "## 评分说明",
            "",
            "| 维度 | 1 分 | 3 分 | 5 分 |",
            "| --- | --- | --- | --- |",
            f"| 可用性 | {catalog['rubric']['usability'][1]} | {catalog['rubric']['usability'][3]} | {catalog['rubric']['usability'][5]} |",
            f"| 完整度 | {catalog['rubric']['completeness'][1]} | {catalog['rubric']['completeness'][3]} | {catalog['rubric']['completeness'][5]} |",
            f"| 维护度 | {catalog['rubric']['maintenance'][1]} | {catalog['rubric']['maintenance'][3]} | {catalog['rubric']['maintenance'][5]} |",
            f"| 隐私友好度 | {catalog['rubric']['privacy_friendliness'][1]} | {catalog['rubric']['privacy_friendliness'][3]} | {catalog['rubric']['privacy_friendliness'][5]} |",
            "",
            "## 人物列表",
            "",
        ]
    )
    for category in ("关系类", "职场类", "思维类", "纪念类"):
        sections.append(category_table(skills, category))
    sections.extend(["---", "", "## 劝告", "", "> 人会走，事会变，话会过期；只有被提炼过的判断、偏爱和牵挂，值得长期保存。", ""])
    return "\n".join(sections)


def main() -> int:
    catalog = load_catalog()
    content = build_readme(catalog)
    README_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote {README_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
