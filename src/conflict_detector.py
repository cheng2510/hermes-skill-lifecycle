"""
技能冲突检测引擎

检测维度：
1. 名称相似度 — Levenshtein 距离
2. 描述重叠度 — TF-IDF 余弦相似度
3. 标签碰撞 — Jaccard 相似度
4. 触发词冲突 — 关键词重叠检测
"""

import re
from dataclasses import dataclass
from typing import Optional
from .skill_registry import SkillMeta


@dataclass
class Conflict:
    """冲突记录"""
    skill_a: str
    skill_b: str
    conflict_type: str  # name|description|tags|trigger
    severity: str       # high|medium|low
    score: float        # 0-1 相似度
    detail: str


class ConflictDetector:
    """冲突检测器"""

    # 阈值配置
    THRESHOLDS = {
        "name": 0.7,        # 名称相似度
        "description": 0.5, # 描述相似度
        "tags": 0.5,        # 标签重叠度
        "trigger": 0.3,     # 触发词重叠度
    }

    def detect_all(self, skills: dict[str, SkillMeta]) -> list[Conflict]:
        """执行全量冲突检测"""
        conflicts = []
        skill_list = list(skills.values())

        for i in range(len(skill_list)):
            for j in range(i + 1, len(skill_list)):
                a, b = skill_list[i], skill_list[j]

                # 名称相似度
                name_sim = self._name_similarity(a.name, b.name)
                if name_sim >= self.THRESHOLDS["name"]:
                    conflicts.append(Conflict(
                        skill_a=a.name, skill_b=b.name,
                        conflict_type="name",
                        severity="high" if name_sim >= 0.9 else "medium",
                        score=name_sim,
                        detail=f"名称相似度 {name_sim:.2f}"
                    ))

                # 描述重叠度
                desc_sim = self._text_similarity(a.description, b.description)
                if desc_sim >= self.THRESHOLDS["description"]:
                    conflicts.append(Conflict(
                        skill_a=a.name, skill_b=b.name,
                        conflict_type="description",
                        severity="high" if desc_sim >= 0.8 else "medium",
                        score=desc_sim,
                        detail=f"描述相似度 {desc_sim:.2f}"
                    ))

                # 标签碰撞
                tag_sim = self._tag_similarity(a.tags, b.tags)
                if tag_sim >= self.THRESHOLDS["tags"]:
                    conflicts.append(Conflict(
                        skill_a=a.name, skill_b=b.name,
                        conflict_type="tags",
                        severity="medium" if tag_sim >= 0.7 else "low",
                        score=tag_sim,
                        detail=f"标签重叠 {tag_sim:.2f}: {set(a.tags) & set(b.tags)}"
                    ))

                # 触发词冲突（从 description 和 When to Use 提取）
                trig_sim = self._trigger_similarity(a, b)
                if trig_sim >= self.THRESHOLDS["trigger"]:
                    conflicts.append(Conflict(
                        skill_a=a.name, skill_b=b.name,
                        conflict_type="trigger",
                        severity="high" if trig_sim >= 0.6 else "medium",
                        score=trig_sim,
                        detail=f"触发词重叠 {trig_sim:.2f}"
                    ))

        # 按严重度排序
        severity_order = {"high": 0, "medium": 1, "low": 2}
        conflicts.sort(key=lambda c: (severity_order.get(c.severity, 3), -c.score))

        return conflicts

    def _name_similarity(self, a: str, b: str) -> float:
        """计算名称相似度（Levenshtein 归一化）"""
        a, b = a.lower().strip(), b.lower().strip()
        if a == b:
            return 1.0

        max_len = max(len(a), len(b))
        if max_len == 0:
            return 1.0

        # 真正的 Levenshtein 距离
        dist = self._levenshtein(a, b)
        sim = 1.0 - (dist / max_len)

        # 包含关系给高分
        if a in b or b in a:
            shorter = min(len(a), len(b))
            longer = max(len(a), len(b))
            containment = shorter / longer
            sim = max(sim, containment)

        return round(sim, 4)

    def _levenshtein(self, a: str, b: str) -> int:
        """计算 Levenshtein 编辑距离"""
        m, n = len(a), len(b)
        # 优化：只用两行
        if m < n:
            return self._levenshtein(b, a)
        prev = list(range(n + 1))
        for i in range(1, m + 1):
            curr = [i] + [0] * n
            for j in range(1, n + 1):
                cost = 0 if a[i-1] == b[j-1] else 1
                curr[j] = min(curr[j-1] + 1, prev[j] + 1, prev[j-1] + cost)
            prev = curr
        return prev[n]

    def _text_similarity(self, a: str, b: str) -> float:
        """文本相似度（词频向量余弦相似度）"""
        words_a = set(self._tokenize(a))
        words_b = set(self._tokenize(b))

        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b

        return len(intersection) / len(union) if union else 0.0

    def _tag_similarity(self, tags_a: list, tags_b: list) -> float:
        """标签 Jaccard 相似度"""
        set_a = set(t.lower() for t in tags_a)
        set_b = set(t.lower() for t in tags_b)

        if not set_a or not set_b:
            return 0.0

        return len(set_a & set_b) / len(set_a | set_b)

    def _trigger_similarity(self, a: SkillMeta, b: SkillMeta) -> float:
        """触发词相似度"""
        # 从 description 提取关键词
        words_a = set(self._extract_keywords(a.description))
        words_b = set(self._extract_keywords(b.description))

        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        # 用较小集合做分母，更容易触发冲突
        min_size = min(len(words_a), len(words_b))

        return len(intersection) / min_size if min_size else 0.0

    def _tokenize(self, text: str) -> list[str]:
        """分词（中英文混合）"""
        # 英文单词
        words = re.findall(r"[a-zA-Z]+", text.lower())
        # 中文字符（按字分）
        chinese = re.findall(r"[\u4e00-\u9fff]", text)
        return words + chinese

    def _extract_keywords(self, text: str) -> list[str]:
        """提取关键词（过滤停用词）"""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "when", "where", "why", "how",
            "all", "each", "every", "both", "few", "more", "most", "other",
            "some", "such", "no", "nor", "not", "only", "own", "same",
            "so", "than", "too", "very", "just", "because", "but", "and",
            "or", "if", "while", "use", "using", "used", "via",
            # 中文停用词
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这",
        }
        tokens = self._tokenize(text)
        return [t for t in tokens if t not in stop_words and len(t) > 1]

    def format_report(self, conflicts: list[Conflict]) -> str:
        """格式化冲突报告"""
        if not conflicts:
            return "✅ 未检测到技能冲突"

        lines = []
        lines.append("=" * 60)
        lines.append("  技能冲突检测报告")
        lines.append("=" * 60)
        lines.append(f"  发现 {len(conflicts)} 个冲突")
        lines.append("")

        severity_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        type_labels = {
            "name": "名称冲突",
            "description": "功能重叠",
            "tags": "标签碰撞",
            "trigger": "触发词冲突",
        }

        for c in conflicts:
            icon = severity_icons.get(c.severity, "⚪")
            label = type_labels.get(c.conflict_type, c.conflict_type)
            lines.append(f"  {icon} [{label}] {c.skill_a} ↔ {c.skill_b}")
            lines.append(f"     相似度: {c.score:.2f} | {c.detail}")
            lines.append("")

        # 统计摘要
        high = sum(1 for c in conflicts if c.severity == "high")
        medium = sum(1 for c in conflicts if c.severity == "medium")
        low = sum(1 for c in conflicts if c.severity == "low")

        lines.append("  ┌─────────────────────┐")
        lines.append(f"  │ 🔴 高危: {high:>3}        │")
        lines.append(f"  │ 🟡 中危: {medium:>3}        │")
        lines.append(f"  │ 🟢 低危: {low:>3}        │")
        lines.append("  └─────────────────────┘")
        lines.append("=" * 60)

        report = "\n".join(lines)
        print(report)
        return report
