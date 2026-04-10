from __future__ import annotations

import base64
import concurrent.futures
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "skills.yaml"
AUDIT_DATE = dt.date.today()
MAX_WORKERS = 8
USER_AGENT = "codex-cli-msb-audit"
GITHUB_API = "https://api.github.com"

SCENE_VOCAB = [
    "失恋",
    "导师学术",
    "求职职场",
    "亲人纪念",
    "自我蒸馏",
    "偶像陪伴",
    "恋爱沟通",
    "亲友陪伴",
    "方法论思考",
    "商业投资",
    "角色扮演",
    "玄学宗教",
]

SOURCE_VOCAB = [
    "公开资料",
    "聊天记录",
    "工作文档",
    "代码记录",
    "社交媒体",
    "多模态遗物",
    "结构化输入",
    "混合来源",
]

RISK_VOCAB = [
    "公开资料型",
    "私密聊天型",
    "纪念型",
    "高情绪依赖型",
]

PRIVACY_LEVELS = ["低", "中", "高", "极高"]
INSTALL_DIFFICULTIES = ["低", "中", "高"]
ACTIVE_BUCKETS = ["30天内活跃", "90天内活跃", "180天内活跃", "180天以上"]
LABEL_VOCAB = ["新手推荐", "研究价值高", "情绪价值强", "方法论强"]
COMPARE_GROUPS = ["前任.skill", "自己.skill", "老板.skill", "导师.skill", "父母.skill", "偶像陪伴"]
REPO_REPLACEMENTS = {
    "Lisaaa1017/friend-skill": "1544501967/friend-skill",
    "berhannnnd/old-geezer-skill": "Pixeldooooog/old-geezer-skill",
}

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".sh",
    ".ps1",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
}

SCENE_RULES = {
    "失恋": ["前任", "ex-skill", "ex skill", "失恋", "分手", "初恋", "意难平", "回不去的夏天", "旧关系", "告别", "复合", "挽回", "旧爱", "想念"],
    "导师学术": ["导师", "mentor", "supervisor", "教授", "professor", "老师", "大学老师", "论文", "paper", "学术", "组会", "答辩", "课题组", "实验"],
    "求职职场": ["同事", "colleague", "老板", "boss", "hr", "招聘", "求职", "客户", "client", "maintainer", "离职", "交接", "公司", "工位", "冷邮件"],
    "亲人纪念": ["父母", "parents", "妈妈", "mama", "亲人", "家人", "家庭", "逝者", "故人", "纪念", "memorial", "重逢", "reunion", "葬礼", "骨灰"],
    "自我蒸馏": ["自己", "yourself", "self", "me-skill", "digital twin", "数字分身", "自我蒸馏", "永生", "clone yourself", "mirror self"],
    "偶像陪伴": ["偶像", "idol", "追星", "明星", "歌手", "内娱", "vtb", "塔菲", "虞书欣", "常昕琦", "kol", "网红", "up主", "creator", "赛博人格", "主播", "虚拟主播", "饭圈", "应援"],
    "恋爱沟通": ["恋爱", "relationship", "暗恋", "crush", "心动", "伴侣", "partner", "表白", "姻缘", "暧昧", "邀约", "沟通", "simp", "情感", "两性", "亲密关系", "回复", "相处", "关系问题"],
    "亲友陪伴": ["朋友", "friend", "兄弟", "bro", "群友", "群聊", "微信好友", "亲友", "师父", "同门", "labmate", "友谊", "陪伴"],
    "方法论思考": ["方法论", "方法", "perspective", "心智模型", "认知", "判断框架", "第一性原理", "战略", "操作系统", "思考框架", "决策"],
    "商业投资": ["投资", "股票", "股东信", "商业", "财富", "finance", "invest", "trader", "加密", "crypto", "市场", "风险", "谈判"],
    "角色扮演": ["扮演", "roleplay", "larp", "角色", "附体", "wiki", "设定", "虚拟主播", "persona", "角色人格"],
    "玄学宗教": ["八字", "命理", "算命", "佛教", "佛陀", "金刚经", "月老", "姻缘测算", "奇门", "紫微", "jesus", "宗教"],
}

SOURCE_RULES = {
    "公开资料": ["公开资料", "公开著作", "公开发言", "公开信息", "公开内容", "wiki", "wikipedia", "论文", "文章", "访谈", "公开人物", "歌词", "公开主页", "股东信", "古籍", "经典", "公众号文章", "公开视频", "演讲", "诸子百家", "公开文献", "公开语料"],
    "聊天记录": ["聊天记录", "chat history", "对话记录", "微信聊天", "qq 聊天", "私聊记录", "群聊记录", "飞书消息", "lark data"],
    "工作文档": ["工作文档", "会议纪要", "会议转写", "项目材料", "评审", "交接", "拒信", "招聘流程", "工作材料", "批注", "飞书", "钉钉", "邮件", "冷邮件", "需求文档"],
    "代码记录": ["代码提交", "github 动态", "commit history", "commit", "pull request", "代码仓库历史", "代码评审", "git log", "issue 记录"],
    "社交媒体": ["微博", "抖音", "b站", "小红书", "公众号", "评论", "社交媒体", "视频", "直播", "social media"],
    "多模态遗物": ["照片", "语音", "视频", "音频", "信件", "数字遗物", "digital relic", "墓志铭"],
    "结构化输入": ["出生信息", "生辰", "四柱", "八字", "问卷", "结构化输入", "questionnaire", "表单", "模板字段", "输入卡片"],
}

RUBRIC = {
    "usability": {1: "几乎无法直接上手", 2: "能看懂但难复现", 3: "可安装可理解", 4: "文档清楚、上手顺畅", 5: "开箱即用、说明完整、路径明确"},
    "completeness": {1: "只有概念", 2: "最小原型", 3: "核心内容齐全", 4: "文档、示例和结构完整", 5: "内容、示例、边界和说明都成熟"},
    "maintenance": {1: "长期停更且仓库粗糙", 2: "偶有维护", 3: "近期有更新或基本可用", 4: "活跃且结构稳定", 5: "持续活跃、维护信号强"},
    "privacy_friendliness": {1: "强依赖高度敏感私密数据", 2: "高度依赖私人记录", 3: "可混合使用公开与私有数据", 4: "公开资料即可体验主体能力", 5: "几乎完全公开资料或本地可控、风险低"},
}


def headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_PAT", "").strip()
    result = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        result["Authorization"] = f"Bearer {token}"
    return result


def request_json(url: str) -> dict | list:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers())
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code in {403, 429, 500, 502, 503, 504} and attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except Exception as error:
            last_error = error
            if attempt < 3:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"GitHub API failed: {last_error}")


def request_text(owner: str, repo: str, path: str, ref: str) -> str | None:
    encoded_path = "/".join(urllib.parse.quote(part) for part in path.split("/"))
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{encoded_path}?ref={urllib.parse.quote(ref)}"
    try:
        data = request_json(url)
    except urllib.error.HTTPError:
        return None
    if not isinstance(data, dict):
        return None
    content = data.get("content", "")
    encoding = data.get("encoding")
    if content and encoding == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", errors="ignore")
        except Exception:
            return None
    download_url = data.get("download_url")
    if download_url:
        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception:
            return None
    return None


def request_readme(owner: str, repo: str, ref: str) -> tuple[str, str | None]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme?ref={urllib.parse.quote(ref)}"
    try:
        data = request_json(url)
    except urllib.error.HTTPError:
        return "README.md", None
    if not isinstance(data, dict):
        return "README.md", None
    path = data.get("path", "README.md")
    content = data.get("content", "")
    if content and data.get("encoding") == "base64":
        try:
            text = base64.b64decode(content).decode("utf-8", errors="ignore")
            return path, text
        except Exception:
            pass
    download_url = data.get("download_url")
    if download_url:
        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as response:
                return path, response.read().decode("utf-8", errors="ignore")
        except Exception:
            return path, None
    return path, None


def request_repo(owner: str, repo: str) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    data = request_json(url)
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid repo response for {owner}/{repo}")
    return data


def request_tree(owner: str, repo: str, ref: str) -> list[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{urllib.parse.quote(ref)}?recursive=1"
    data = request_json(url)
    if not isinstance(data, dict):
        return []
    return data.get("tree", [])


def is_text_path(path: str) -> bool:
    lower = path.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".pdf", ".zip", ".mp4", ".mp3", ".wav", ".docx")):
        return False
    suffix = Path(lower).suffix
    if suffix in TEXT_EXTENSIONS:
        return True
    return suffix == "" and "." not in Path(lower).name


def shortest_path(paths: list[str]) -> str | None:
    if not paths:
        return None
    return sorted(paths, key=lambda item: (item.count("/"), len(item), item.lower()))[0]


def choose_paths(tree: list[dict], readme_path: str) -> list[str]:
    blob_paths = [item["path"] for item in tree if item.get("type") == "blob"]
    selected: list[str] = []
    if readme_path:
        selected.append(readme_path)
    skill_paths = [path for path in blob_paths if path.lower().endswith("skill.md")]
    skill_path = shortest_path(skill_paths)
    if skill_path and skill_path not in selected:
        selected.append(skill_path)
    for prefix in ("prompts/", "src/", "tools/", "examples/"):
        candidates = [path for path in blob_paths if path.startswith(prefix) and is_text_path(path) and not path.lower().endswith("readme.md")]
        candidate = shortest_path(candidates)
        if candidate and candidate not in selected:
            selected.append(candidate)
    for manifest_name in ("meta.json", "package.json", "requirements.txt"):
        manifest_candidates = [path for path in blob_paths if path.lower().endswith(manifest_name)]
        manifest = shortest_path(manifest_candidates)
        if manifest and manifest not in selected:
            selected.append(manifest)
    deduped: list[str] = []
    for item in selected:
        if item not in deduped:
            deduped.append(item)
    return deduped[:4]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def contains_keyword(text: str, keyword: str) -> bool:
    normalized_text = normalize_text(text)
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return False
    if re.search(r"[\u4e00-\u9fff]", normalized_keyword):
        return normalized_keyword in normalized_text
    pattern = r"(?<![a-z0-9])" + re.escape(normalized_keyword) + r"(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None


def score_keywords(text: str, keywords: list[str]) -> int:
    total = 0
    for keyword in keywords:
        if contains_keyword(text, keyword):
            total += 1
    return total


def determine_scene_tags(text: str, category: str) -> list[str]:
    scored = [(tag, score_keywords(text, keywords)) for tag, keywords in SCENE_RULES.items()]
    matched = [tag for tag, score in sorted(scored, key=lambda item: (-item[1], item[0])) if score > 0]
    if matched:
        return matched[:3]
    fallback = {"关系类": ["亲友陪伴"], "职场类": ["求职职场"], "思维类": ["方法论思考"], "纪念类": ["亲人纪念"]}
    return fallback.get(category, ["方法论思考"])


def determine_source_types(text: str, category: str) -> list[str]:
    scored = [(source, score_keywords(text, keywords)) for source, keywords in SOURCE_RULES.items()]
    matched = [source for source, score in sorted(scored, key=lambda item: (-item[1], SOURCE_VOCAB.index(item[0]))) if score > 0]
    if matched:
        ordered = matched[:2]
        if len(matched) > 1:
            ordered.append("混合来源")
        return ordered
    fallback = {"关系类": ["聊天记录"], "职场类": ["工作文档"], "思维类": ["公开资料"], "纪念类": ["多模态遗物", "混合来源"]}
    return fallback.get(category, ["混合来源"])


def determine_privacy_level(scene_tags: list[str], source_types: list[str]) -> str:
    sources = set(source_types)
    scenes = set(scene_tags)
    if "多模态遗物" in sources and ("聊天记录" in sources or "亲人纪念" in scenes):
        return "极高"
    if "聊天记录" in sources and ("亲人纪念" in scenes or "失恋" in scenes or "恋爱沟通" in scenes):
        return "极高"
    if "聊天记录" in sources or "工作文档" in sources or "代码记录" in sources:
        return "高"
    if "混合来源" in sources or "社交媒体" in sources:
        return "中"
    return "低"


def determine_risk_tags(scene_tags: list[str], source_types: list[str]) -> list[str]:
    result: list[str] = []
    scenes = set(scene_tags)
    sources = set(source_types)
    if sources <= {"公开资料", "社交媒体"} or ("公开资料" in sources and "聊天记录" not in sources and "工作文档" not in sources):
        result.append("公开资料型")
    if "聊天记录" in sources or "工作文档" in sources or "代码记录" in sources:
        result.append("私密聊天型")
    if "亲人纪念" in scenes:
        result.append("纪念型")
    if scenes & {"失恋", "恋爱沟通", "亲人纪念", "偶像陪伴"}:
        result.append("高情绪依赖型")
    if not result:
        result.append("公开资料型")
    return [item for item in RISK_VOCAB if item in result]


def determine_focus_object(name: str, scene_tags: list[str], text: str) -> str:
    normalized_name = normalize_text(name)
    if "自己" in name or "self" in normalized_name or "distillme" in normalized_name or "数字分身" in name or "digital twin" in normalized_name:
        return "自己 / 数字分身"
    if "父母" in name or "妈妈" in name or "parents" in normalized_name or "mama" in normalized_name:
        return "父母 / 家庭记忆"
    if any(keyword in name for keyword in ["朋友", "群友", "兄弟", "师父", "同门"]) or "friend" in normalized_name:
        return "朋友 / 群友 / 同伴"
    if "前任" in name or re.search(r"(?<![a-z0-9])ex(?:[- ]?(?:skill|partner|girlfriend|boyfriend|friend))?(?![a-z0-9])", normalized_name):
        return "前任 / 旧关系"
    if "老板" in name or "boss" in normalized_name:
        return "老板 / 管理者"
    if "导师" in name or "mentor" in normalized_name or "supervisor" in normalized_name or "professor" in normalized_name:
        return "导师 / 学术指导"
    if scene_tags and "偶像陪伴" in scene_tags:
        return "偶像 / 创作者 / 虚拟主播"
    if scene_tags and "亲人纪念" in scene_tags:
        return "亲人 / 逝者 / 纪念对象"
    if scene_tags and "亲友陪伴" in scene_tags:
        return "朋友 / 群友 / 同伴"
    primary_scene = scene_tags[0] if scene_tags else ""
    if primary_scene == "求职职场":
        return "职场角色 / 工作关系"
    if primary_scene == "恋爱沟通":
        return "亲密关系对象"
    if primary_scene in {"方法论思考", "商业投资"}:
        return "公开人物 / 方法论视角"
    return name


def determine_install_difficulty(tree: list[dict], readme_text: str, skill_md_verified: bool) -> str:
    blob_paths = [item["path"] for item in tree if item.get("type") == "blob"]
    has_manifest = any(path.lower().endswith(("package.json", "requirements.txt", "pyproject.toml")) for path in blob_paths)
    has_code_dir = any(path.startswith(("src/", "tools/", "scripts/")) for path in blob_paths)
    has_examples = any(path.startswith("examples/") for path in blob_paths)
    lowered = normalize_text(readme_text)
    explicit_setup = any(keyword in lowered for keyword in ["安装", "install", "快速开始", "quick start", "运行", "usage", "pip install", "npm install"])
    if has_manifest and has_code_dir and (len(blob_paths) > 30 or has_examples):
        return "高"
    if has_manifest or has_code_dir or has_examples or explicit_setup:
        return "中"
    if skill_md_verified and len(blob_paths) <= 15:
        return "低"
    return "中"


def determine_beginner_friendly(readme_text: str, install_difficulty: str, skill_md_verified: bool) -> bool:
    lowered = normalize_text(readme_text)
    has_usage = any(keyword in lowered for keyword in ["快速开始", "quick start", "使用方法", "usage", "安装", "install", "运行"])
    if install_difficulty == "低" and (has_usage or skill_md_verified):
        return True
    if install_difficulty == "中" and has_usage and skill_md_verified:
        return True
    return False


def active_bucket(pushed_at: str, audited_at: dt.date) -> str:
    pushed_date = dt.datetime.fromisoformat(pushed_at.replace("Z", "+00:00")).date()
    delta = (audited_at - pushed_date).days
    if delta <= 30:
        return "30天内活跃"
    if delta <= 90:
        return "90天内活跃"
    if delta <= 180:
        return "180天内活跃"
    return "180天以上"


def score_usability(readme_text: str, install_difficulty: str, beginner_friendly: bool, skill_md_verified: bool) -> int:
    score = 3
    if beginner_friendly:
        score += 1
    if install_difficulty == "低":
        score += 1
    if install_difficulty == "高":
        score -= 1
    if not skill_md_verified:
        score -= 1
    if len(readme_text or "") < 400:
        score -= 1
    return max(1, min(5, score))


def score_completeness(tree: list[dict], readme_text: str, skill_md_verified: bool) -> int:
    blob_paths = [item["path"] for item in tree if item.get("type") == "blob"]
    features = 0
    if readme_text:
        features += 1
    if skill_md_verified:
        features += 1
    if any(path.startswith(("prompts/", "tools/", "src/", "examples/")) for path in blob_paths):
        features += 1
    if any(path.lower().endswith(("meta.json", "package.json", "requirements.txt", "pyproject.toml")) for path in blob_paths):
        features += 1
    if len(readme_text or "") > 1200 or len(blob_paths) > 20:
        features += 1
    mapping = {0: 1, 1: 2, 2: 3, 3: 4}
    return mapping.get(features, 5)


def score_maintenance(tree: list[dict], pushed_at: str, audited_at: dt.date, skill_md_verified: bool) -> int:
    bucket = active_bucket(pushed_at, audited_at)
    score = {"30天内活跃": 5, "90天内活跃": 4, "180天内活跃": 3, "180天以上": 2}[bucket]
    blob_count = len([item for item in tree if item.get("type") == "blob"])
    if blob_count < 5 and not skill_md_verified:
        score -= 1
    return max(1, min(5, score))


def score_privacy_friendliness(privacy_level: str, source_types: list[str]) -> int:
    if privacy_level == "低":
        return 5
    if privacy_level == "中":
        return 4
    if privacy_level == "高":
        return 2 if "公开资料" not in source_types else 3
    return 1


def determine_labels(scene_tags: list[str], install_difficulty: str, beginner_friendly: bool, scores: dict[str, int], tree: list[dict], category: str) -> list[str]:
    labels: list[str] = []
    if beginner_friendly and install_difficulty != "高" and scores["usability"] >= 4 and scores["completeness"] >= 4:
        labels.append("新手推荐")
    blob_paths = [item["path"] for item in tree if item.get("type") == "blob"]
    if scores["completeness"] >= 4 and any(path.startswith(("src/", "tools/", "scripts/", "examples/")) for path in blob_paths):
        labels.append("研究价值高")
    if set(scene_tags) & {"失恋", "恋爱沟通", "亲人纪念", "偶像陪伴", "亲友陪伴"}:
        labels.append("情绪价值强")
    if category == "思维类" or set(scene_tags) & {"方法论思考", "商业投资", "导师学术"}:
        labels.append("方法论强")
    return [item for item in LABEL_VOCAB if item in labels]


def determine_compare_groups(name: str, scene_tags: list[str], focus_object: str) -> list[str]:
    groups: list[str] = []
    normalized = name.lower()
    if "前任" in name or normalized.startswith("ex.") or "ex-skill" in normalized:
        groups.append("前任.skill")
    if "自己" in name or "self" in normalized or "distillme" in normalized or "数字分身" in name or "digital twin" in normalized:
        groups.append("自己.skill")
    if "老板" in name or "boss" in normalized or "laoban" in normalized:
        groups.append("老板.skill")
    if "导师" in name or "mentor" in normalized or "supervisor" in normalized or "professor" in normalized or "老师" in name:
        groups.append("导师.skill")
    if "父母" in name or "妈妈" in name or "mama" in normalized or "family" in normalized:
        groups.append("父母.skill")
    if "偶像陪伴" in scene_tags or focus_object == "偶像 / 创作者 / 虚拟主播":
        groups.append("偶像陪伴")
    deduped: list[str] = []
    for item in groups:
        if item not in deduped:
            deduped.append(item)
    return [item for item in COMPARE_GROUPS if item in deduped]


def build_compare_note(source_types: list[str], risk_tags: list[str], install_difficulty: str, focus_object: str) -> str:
    source_text = "、".join([item for item in source_types if item != "混合来源"][:2]) or "混合来源"
    risk_text = "、".join(risk_tags[:2])
    return f"核心对象是{focus_object}，主要依赖{source_text}，风险侧重{risk_text}，安装难度{install_difficulty}。"


def find_source_fact(text: str, source_types: list[str]) -> str:
    sources = set(source_types)
    if "聊天记录" in sources and contains_keyword(text, "聊天记录"):
        return "README 明确提到使用聊天记录"
    if "聊天记录" in sources and (contains_keyword(text, "飞书消息") or contains_keyword(text, "lark data") or contains_keyword(text, "feishu")):
        return "README 明确提到使用飞书消息数据"
    if "聊天记录" in sources and contains_keyword(text, "微信聊天"):
        return "README 明确提到使用微信数据"
    if "多模态遗物" in sources and contains_keyword(text, "照片") and contains_keyword(text, "语音"):
        return "README 明确提到结合照片与语音等多模态材料"
    if "公开资料" in sources and any(contains_keyword(text, item) for item in ["公开资料", "公开发言", "公开著作", "公开文献", "诸子百家", "古籍", "股东信"]):
        return "README 明确提到以公开资料为输入"
    if "公开资料" in sources and contains_keyword(text, "公众号"):
        return "README 明确提到以公众号文章为主要来源"
    if "公开资料" in sources and contains_keyword(text, "论文"):
        return "README 明确提到以论文或公开文献为输入"
    if "公开资料" in sources and contains_keyword(text, "wiki"):
        return "README 明确提到以 Wiki 或公开设定为输入"
    if "结构化输入" in sources and (contains_keyword(text, "八字") or contains_keyword(text, "生辰")):
        return "README 明确提到通过结构化命理输入驱动分析"
    if "社交媒体" in sources and any(contains_keyword(text, item) for item in ["社交媒体", "微博", "抖音", "b站", "小红书", "公开视频"]):
        return "README 明确提到从社交媒体内容中提炼"
    if source_types == ["混合来源"]:
        return "README 没有完全写清单一来源，仓库更像混合资料驱动的 skill"
    if "公开资料" in source_types:
        return "仓库文本主要指向公开资料驱动的 skill"
    if "聊天记录" in source_types:
        return "仓库文本主要指向聊天记录驱动的 skill"
    return "README 与仓库结构共同显示该项目围绕特定资料源进行蒸馏"


def build_evidence_summary(readme_path: str, text: str, source_types: list[str], skill_md_verified: bool, skill_md_location: str, inspected_files: list[str], install_difficulty: str, scene_tags: list[str]) -> str:
    source_fact = find_source_fact(text, source_types)
    structure_bits: list[str] = []
    if Path(readme_path).name.lower().startswith("readme"):
        structure_bits.append(f"主说明文档为 `{readme_path}`")
    else:
        structure_bits.append(f"仓库未提供 README，改以 `{readme_path}` 作为主说明文档")
    if skill_md_verified:
        if skill_md_location == "root":
            structure_bits.append("仓库根目录包含 `SKILL.md`")
        else:
            structure_bits.append("仓库子目录中包含 `SKILL.md`")
    else:
        structure_bits.append("仓库未找到 `SKILL.md`")
    for prefix in ("prompts/", "src/", "tools/", "examples/"):
        if any(path.startswith(prefix) for path in inspected_files):
            structure_bits.append(f"本次审阅还查看了 `{prefix}` 下代表文件")
            break
    if not any(path.endswith(("package.json", "requirements.txt", "meta.json")) for path in inspected_files):
        structure_bits.append("实现信号主要集中在说明文档与少量核心文件")
    scene_text = "、".join(scene_tags[:2])
    structure_text = "，".join(structure_bits)
    return f"{source_fact}，{structure_text}，因此判定为{scene_text}相关项目，安装难度{install_difficulty}。"


def ensure_metadata(catalog: dict) -> dict:
    catalog["meta"] = {
        "title": "MSB Skills 万魂幡",
        "audited_at": AUDIT_DATE.isoformat(),
        "total_skills": len(catalog.get("skills", [])),
        "source": "GitHub repository audit",
        "featured_scenes": ["失恋", "导师学术", "求职职场", "亲人纪念", "自我蒸馏", "偶像陪伴"],
        "compare_groups_order": COMPARE_GROUPS,
    }
    catalog["vocab"] = {
        "scene_tags": SCENE_VOCAB,
        "source_types": SOURCE_VOCAB,
        "risk_tags": RISK_VOCAB,
        "privacy_levels": PRIVACY_LEVELS,
        "install_difficulties": INSTALL_DIFFICULTIES,
        "active_buckets": ACTIVE_BUCKETS,
        "labels": LABEL_VOCAB,
    }
    catalog["rubric"] = RUBRIC
    return catalog


def load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Missing catalog file: {CATALOG_PATH}")
    with CATALOG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def save_catalog(catalog: dict) -> None:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_PATH.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(catalog, handle, allow_unicode=True, sort_keys=False, width=120)


def skill_id_from_repo(repo: str) -> str:
    owner, name = repo.split("/", 1)
    return f"{owner.lower()}--{name.lower()}"


def audit_skill(skill: dict) -> dict:
    resolved_repo = REPO_REPLACEMENTS.get(skill["repo"], skill["repo"])
    owner, repo = resolved_repo.split("/", 1)
    repo_info = request_repo(owner, repo)
    default_branch = repo_info.get("default_branch", "main")
    tree = request_tree(owner, repo, default_branch)
    readme_path, readme_text = request_readme(owner, repo, default_branch)
    if not readme_text:
        blob_paths = [item["path"] for item in tree if item.get("type") == "blob"]
        fallback_readmes = [path for path in blob_paths if Path(path).name.lower().startswith("readme")]
        fallback_readme = shortest_path(fallback_readmes)
        if fallback_readme:
            fallback_text = request_text(owner, repo, fallback_readme, default_branch)
            if fallback_text:
                readme_path = fallback_readme
                readme_text = fallback_text
        else:
            skill_md_fallback = shortest_path([path for path in blob_paths if path.lower().endswith("skill.md")])
            if skill_md_fallback:
                fallback_text = request_text(owner, repo, skill_md_fallback, default_branch)
                if fallback_text:
                    readme_path = skill_md_fallback
                    readme_text = fallback_text
    chosen_paths = choose_paths(tree, readme_path)
    inspected_files: list[str] = []
    inspected_texts: list[str] = []
    if readme_text:
        inspected_files.append(readme_path)
        inspected_texts.append(readme_text)
    blob_paths = {item["path"] for item in tree if item.get("type") == "blob"}
    skill_md_paths = sorted([path for path in blob_paths if path.lower().endswith("skill.md")], key=lambda item: (item.count("/"), len(item), item))
    skill_md_path = skill_md_paths[0] if skill_md_paths else None
    if skill_md_path and skill_md_path not in inspected_files:
        text = request_text(owner, repo, skill_md_path, default_branch)
        if text:
            inspected_files.append(skill_md_path)
            inspected_texts.append(text)
    for path in chosen_paths:
        if path in inspected_files:
            continue
        text = request_text(owner, repo, path, default_branch)
        if text:
            inspected_files.append(path)
            inspected_texts.append(text)
        if len(inspected_files) >= 4:
            break
    if len(inspected_files) < 2 and blob_paths:
        fallback_candidates = [path for path in sorted(blob_paths, key=lambda item: (item.count("/"), len(item), item)) if path not in inspected_files and is_text_path(path)]
        for path in fallback_candidates:
            text = request_text(owner, repo, path, default_branch)
            if text:
                inspected_files.append(path)
                inspected_texts.append(text)
            if len(inspected_files) >= 2:
                break
    aggregated_text = "\n".join([repo_info.get("description", "") or "", readme_text or "", *inspected_texts])
    scene_tags = determine_scene_tags(aggregated_text, skill["category"])
    source_types = determine_source_types(aggregated_text, skill["category"])
    privacy_level = determine_privacy_level(scene_tags, source_types)
    risk_tags = determine_risk_tags(scene_tags, source_types)
    skill_md_verified = bool(skill_md_path)
    skill_md_location = "root" if skill_md_path == "SKILL.md" else "subdir" if skill_md_path else "none"
    install_difficulty = determine_install_difficulty(tree, readme_text or "", skill_md_verified)
    beginner_friendly = determine_beginner_friendly(readme_text or "", install_difficulty, skill_md_verified)
    pushed_at = repo_info["pushed_at"]
    scores = {
        "usability": score_usability(readme_text or "", install_difficulty, beginner_friendly, skill_md_verified),
        "completeness": score_completeness(tree, readme_text or "", skill_md_verified),
        "maintenance": score_maintenance(tree, pushed_at, AUDIT_DATE, skill_md_verified),
        "privacy_friendliness": score_privacy_friendliness(privacy_level, source_types),
    }
    focus_object = determine_focus_object(skill["name"], scene_tags, aggregated_text)
    compare_group = determine_compare_groups(skill["name"], scene_tags, focus_object)
    compare_note = build_compare_note(source_types, risk_tags, install_difficulty, focus_object)
    labels = determine_labels(scene_tags, install_difficulty, beginner_friendly, scores, tree, skill["category"])
    evidence_summary = build_evidence_summary(readme_path, aggregated_text, source_types, skill_md_verified, skill_md_location, inspected_files, install_difficulty, scene_tags)
    skill.update(
        {
            "id": skill_id_from_repo(resolved_repo),
            "repo": resolved_repo,
            "url": f"https://github.com/{resolved_repo}",
            "focus_object": focus_object,
            "scene_tags": scene_tags,
            "source_types": source_types,
            "privacy_level": privacy_level,
            "risk_tags": risk_tags,
            "skill_md_verified": skill_md_verified,
            "skill_md_location": skill_md_location,
            "install_difficulty": install_difficulty,
            "beginner_friendly": beginner_friendly,
            "last_pushed_at": pushed_at[:10],
            "active_bucket": active_bucket(pushed_at, AUDIT_DATE),
            "audit": {
                "readme_checked": bool(readme_text),
                "inspected_files": inspected_files[:4],
                "evidence_summary": evidence_summary,
                "checked_at": AUDIT_DATE.isoformat(),
                "review_method": "manual_repo_audit",
            },
            "scores": scores,
            "labels": labels,
            "compare_group": compare_group,
            "compare_note": compare_note,
        }
    )
    return skill


def main() -> int:
    if "GITHUB_PAT" not in os.environ or not os.environ["GITHUB_PAT"].strip():
        print("GITHUB_PAT is required.", file=sys.stderr)
        return 1
    catalog = ensure_metadata(load_catalog())
    skills = catalog.get("skills", [])
    audited: list[dict] = [None] * len(skills)
    print(f"Auditing {len(skills)} repositories...", file=sys.stderr)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(audit_skill, dict(skill)): index for index, skill in enumerate(skills)}
        completed = 0
        for future in concurrent.futures.as_completed(future_map):
            index = future_map[future]
            skill = skills[index]
            try:
                audited[index] = future.result()
                completed += 1
                print(f"[{completed}/{len(skills)}] {skill['repo']}", file=sys.stderr)
            except Exception as error:
                raise RuntimeError(f"Failed auditing {skill['repo']}: {error}") from error
    catalog["skills"] = audited
    catalog["meta"]["total_skills"] = len(audited)
    catalog["meta"]["audited_at"] = AUDIT_DATE.isoformat()
    save_catalog(catalog)
    print(f"Updated {CATALOG_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
