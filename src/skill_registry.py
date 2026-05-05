"""
技能注册表 + 健康度评分引擎

核心职责：
1. 扫描 ~/.hermes/skills/ 目录，解析所有 SKILL.md
2. 计算每个技能的健康度评分（0-100）
3. 将技能分为核心/候选/观察/待淘汰四个层级
4. 生成生态健康报告
"""

import os
import re
import yaml
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta


@dataclass
class SkillMeta:
    """技能元数据"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "unknown"
    tags: list = field(default_factory=list)
    related_skills: list = field(default_factory=list)
    category: str = ""
    file_path: str = ""
    # 运行时计算
    health_score: float = 0.0
    tier: str = "unknown"
    usage_count_30d: int = 0
    success_rate: float = 0.0
    last_used_days_ago: int = -1
    doc_length: int = 0
    has_when_to_use: bool = False
    has_pitfalls: bool = False
    has_verification: bool = False


class SkillRegistry:
    """技能注册表"""

    TIERS = {
        "core": (80, 100, "🟢 核心技能"),
        "candidate": (60, 79, "🔵 候选技能"),
        "watch": (40, 59, "🟡 观察技能"),
        "deprecated": (0, 39, "🔴 待淘汰技能"),
    }

    # 健康度权重
    WEIGHTS = {
        "usage_frequency": 0.30,
        "success_rate": 0.25,
        "freshness": 0.20,
        "dependency": 0.15,
        "doc_completeness": 0.10,
    }

    def __init__(self, skills_dir: str = None, db_path: str = None):
        self.skills_dir = Path(skills_dir or os.path.expanduser("~/.hermes/skills"))
        self.db_path = Path(db_path or os.path.expanduser("~/.hermes/skill_lifecycle.db"))
        self.skills: dict[str, SkillMeta] = {}

    def scan_all(self) -> dict[str, SkillMeta]:
        """扫描所有技能目录，解析 SKILL.md"""
        self.skills.clear()

        if not self.skills_dir.exists():
            print(f"[!] 技能目录不存在: {self.skills_dir}")
            return self.skills

        for skill_file in self.skills_dir.rglob("SKILL.md"):
            try:
                meta = self._parse_skill_file(skill_file)
                if meta:
                    self.skills[meta.name] = meta
            except Exception as e:
                print(f"[!] 解析失败 {skill_file}: {e}")

        # 加载使用数据
        self._load_usage_data()

        # 计算健康度
        for skill in self.skills.values():
            skill.health_score = self._calculate_health(skill)
            skill.tier = self._classify_tier(skill.health_score)

        return self.skills

    def _parse_skill_file(self, path: Path) -> Optional[SkillMeta]:
        """解析单个 SKILL.md 文件"""
        content = path.read_text(encoding="utf-8")

        if not content.startswith("---"):
            return None

        # 提取 frontmatter
        match = re.search(r"\n---\s*\n", content[3:])
        if not match:
            return None

        fm_text = content[3:match.start() + 3]
        try:
            fm = yaml.safe_load(fm_text)
        except yaml.YAMLError:
            return None

        if not isinstance(fm, dict):
            return None

        name = fm.get("name", "")
        description = fm.get("description", "")

        if not name or not description:
            return None

        # 提取 metadata
        metadata = fm.get("metadata", {})
        hermes = metadata.get("hermes", {}) if isinstance(metadata, dict) else {}

        # 推断 category
        parts = path.parts
        category = ""
        for i, part in enumerate(parts):
            if part == "skills" and i + 1 < len(parts) - 1:
                category = parts[i + 1]
                break

        body = content[match.end() + 3:]

        return SkillMeta(
            name=name,
            description=description,
            version=fm.get("version", "1.0.0"),
            author=fm.get("author", "unknown"),
            tags=hermes.get("tags", []),
            related_skills=hermes.get("related_skills", []),
            category=category,
            file_path=str(path),
            doc_length=len(body),
            has_when_to_use=bool(re.search(r"#+\s*(When to Use|触发条件)", body, re.I)),
            has_pitfalls=bool(re.search(r"#+\s*(Pitfalls|常见问题|踩坑)", body, re.I)),
            has_verification=bool(re.search(r"#+\s*(Verification|验证|Checklist)", body, re.I)),
        )

    def _load_usage_data(self):
        """从 SQLite 加载使用数据"""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usage_events'")
            if not cursor.fetchone():
                return

            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()

            for skill in self.skills.values():
                # 30天使用次数
                cursor.execute(
                    "SELECT COUNT(*) FROM usage_events WHERE skill_name=? AND timestamp>=?",
                    (skill.name, thirty_days_ago)
                )
                skill.usage_count_30d = cursor.fetchone()[0]

                # 成功率
                cursor.execute(
                    "SELECT COUNT(*) as total, SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as ok "
                    "FROM usage_events WHERE skill_name=?",
                    (skill.name,)
                )
                row = cursor.fetchone()
                if row[0] > 0:
                    skill.success_rate = row[1] / row[0]

                # 最后使用时间
                cursor.execute(
                    "SELECT MAX(timestamp) FROM usage_events WHERE skill_name=?",
                    (skill.name,)
                )
                last = cursor.fetchone()[0]
                if last:
                    last_dt = datetime.fromisoformat(last)
                    skill.last_used_days_ago = (datetime.now() - last_dt).days

        except sqlite3.Error as e:
            print(f"[!] 数据库读取错误: {e}")
        finally:
            conn.close()

    def _calculate_health(self, skill: SkillMeta) -> float:
        """计算技能健康度评分（0-100）"""
        scores = {}

        # 1. 使用频率（30天内调用次数，归一化到0-100）
        # 0次=0, 1-5次=40, 6-20次=70, 20+=100
        count = skill.usage_count_30d
        if count == 0:
            scores["usage_frequency"] = 0
        elif count <= 5:
            scores["usage_frequency"] = 40
        elif count <= 20:
            scores["usage_frequency"] = 70
        else:
            scores["usage_frequency"] = 100

        # 2. 成功率
        scores["success_rate"] = skill.success_rate * 100

        # 3. 新鲜度（越近越好）
        days = skill.last_used_days_ago
        if days < 0:
            scores["freshness"] = 30  # 从未使用，给个基础分
        elif days <= 7:
            scores["freshness"] = 100
        elif days <= 30:
            scores["freshness"] = 70
        elif days <= 90:
            scores["freshness"] = 40
        else:
            scores["freshness"] = 10

        # 4. 依赖度（被其他技能引用的次数）
        ref_count = sum(
            1 for s in self.skills.values()
            if skill.name in s.related_skills
        )
        scores["dependency"] = min(ref_count * 25, 100)

        # 5. 文档完整度
        doc_score = 0
        if skill.doc_length > 500:
            doc_score += 30
        if skill.has_when_to_use:
            doc_score += 25
        if skill.has_pitfalls:
            doc_score += 25
        if skill.has_verification:
            doc_score += 20
        scores["doc_completeness"] = doc_score

        # 加权求和
        total = sum(
            scores[key] * weight
            for key, weight in self.WEIGHTS.items()
        )

        return round(total, 1)

    def _classify_tier(self, score: float) -> str:
        """根据健康分分类层级"""
        for tier_name, (low, high, _) in self.TIERS.items():
            if low <= score <= high:
                return tier_name
        return "deprecated"

    def generate_report(self) -> str:
        """生成生态健康报告"""
        if not self.skills:
            self.scan_all()

        lines = []
        lines.append("=" * 60)
        lines.append("  Hermes Agent 技能生态健康报告")
        lines.append("=" * 60)
        lines.append(f"  扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  技能总数: {len(self.skills)}")
        lines.append("")

        # 分层统计
        tier_counts = {t: 0 for t in self.TIERS}
        for skill in self.skills.values():
            tier_counts[skill.tier] = tier_counts.get(skill.tier, 0) + 1

        lines.append("  ┌─────────────┬───────┐")
        lines.append("  │ 层级         │ 数量  │")
        lines.append("  ├─────────────┼───────┤")
        for tier_name, (_, _, label) in self.TIERS.items():
            count = tier_counts.get(tier_name, 0)
            lines.append(f"  │ {label:<10} │ {count:>5} │")
        lines.append("  └─────────────┴───────┘")
        lines.append("")

        # 按健康分排序
        sorted_skills = sorted(self.skills.values(), key=lambda s: s.health_score, reverse=True)

        lines.append("  技能健康度排行:")
        lines.append("  " + "-" * 56)
        for i, skill in enumerate(sorted_skills, 1):
            tier_label = self.TIERS[skill.tier][2] if skill.tier in self.TIERS else "❓"
            bar_len = int(skill.health_score / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(
                f"  {i:>2}. [{tier_label}] {skill.health_score:>5.1f} "
                f"|{bar}| {skill.name}"
            )

        lines.append("")
        lines.append("=" * 60)

        report = "\n".join(lines)
        print(report)
        return report

    def get_skill(self, name: str) -> Optional[SkillMeta]:
        return self.skills.get(name)

    def list_by_tier(self, tier: str) -> list[SkillMeta]:
        return [s for s in self.skills.values() if s.tier == tier]
