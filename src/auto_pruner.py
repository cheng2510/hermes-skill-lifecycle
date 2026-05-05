"""
自动清理建议引擎

基于健康度评分和使用数据，生成清理建议。
支持 dry-run 模式，不会实际删除任何文件。
"""

from dataclasses import dataclass
from .skill_registry import SkillRegistry, SkillMeta


@dataclass
class PruneAction:
    """清理动作"""
    skill_name: str
    action: str        # deprecate|remove|merge
    reason: str
    severity: str      # safe|caution|danger
    health_score: float
    related_skills: list


class AutoPruner:
    """自动清理器"""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def analyze(self) -> list[PruneAction]:
        """分析并生成清理建议"""
        actions = []

        for skill in self.registry.skills.values():
            # 健康度过低 → 建议淘汰
            if skill.health_score < 30:
                actions.append(PruneAction(
                    skill_name=skill.name,
                    action="deprecate",
                    reason=f"健康度过低 ({skill.health_score:.1f}/100)",
                    severity="safe",
                    health_score=skill.health_score,
                    related_skills=skill.related_skills,
                ))

            # 长期未使用（90天+）且无依赖 → 建议移除
            if skill.last_used_days_ago > 90 and not self._has_dependents(skill):
                actions.append(PruneAction(
                    skill_name=skill.name,
                    action="remove",
                    reason=f"超过 {skill.last_used_days_ago} 天未使用，且无其他技能依赖",
                    severity="caution" if skill.last_used_days_ago < 180 else "safe",
                    health_score=skill.health_score,
                    related_skills=skill.related_skills,
                ))

            # 成功率极低 → 建议修复或移除
            if skill.success_rate < 0.2 and skill.usage_count_30d >= 3:
                actions.append(PruneAction(
                    skill_name=skill.name,
                    action="deprecate",
                    reason=f"成功率过低 ({skill.success_rate:.0%})，可能已失效",
                    severity="safe",
                    health_score=skill.health_score,
                    related_skills=skill.related_skills,
                ))

        # 检测可合并的技能
        merge_suggestions = self._find_merge_candidates()
        actions.extend(merge_suggestions)

        # 去重
        seen = set()
        unique_actions = []
        for a in actions:
            key = (a.skill_name, a.action)
            if key not in seen:
                seen.add(key)
                unique_actions.append(a)

        # 按严重度排序
        severity_order = {"safe": 0, "caution": 1, "danger": 2}
        unique_actions.sort(key=lambda a: (severity_order.get(a.severity, 3), a.health_score))

        return unique_actions

    def _has_dependents(self, skill: SkillMeta) -> bool:
        """检查是否有其他技能依赖此技能"""
        for other in self.registry.skills.values():
            if skill.name in other.related_skills:
                return True
        return False

    def _find_merge_candidates(self) -> list[PruneAction]:
        """找到可以合并的技能对"""
        from .conflict_detector import ConflictDetector

        detector = ConflictDetector()
        conflicts = detector.detect_all(self.registry.skills)

        merge_candidates = []
        seen_pairs = set()

        for c in conflicts:
            if c.severity == "high" and c.conflict_type in ("description", "name"):
                pair = tuple(sorted([c.skill_a, c.skill_b]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    merge_candidates.append(PruneAction(
                        skill_name=f"{c.skill_a} + {c.skill_b}",
                        action="merge",
                        reason=f"{c.detail}，建议合并为一个技能",
                        severity="caution",
                        health_score=max(
                            self.registry.skills.get(c.skill_a, SkillMeta("", "")).health_score,
                            self.registry.skills.get(c.skill_b, SkillMeta("", "")).health_score,
                        ),
                        related_skills=[c.skill_a, c.skill_b],
                    ))

        return merge_candidates

    def format_report(self, actions: list[PruneAction], dry_run: bool = True) -> str:
        """格式化清理报告"""
        lines = []
        lines.append("=" * 60)
        mode = "🔍 DRY-RUN 模式（仅报告，不执行）" if dry_run else "⚠️  执行模式"
        lines.append(f"  技能清理建议 — {mode}")
        lines.append("=" * 60)

        if not actions:
            lines.append("  ✅ 当前无需清理的技能")
            lines.append("=" * 60)
            return "\n".join(lines)

        action_icons = {"deprecate": "📉", "remove": "🗑️", "merge": "🔗"}
        action_labels = {"deprecate": "淘汰", "remove": "移除", "merge": "合并"}
        severity_icons = {"safe": "🟢", "caution": "🟡", "danger": "🔴"}

        for a in actions:
            icon = action_icons.get(a.action, "❓")
            label = action_labels.get(a.action, a.action)
            sev_icon = severity_icons.get(a.severity, "⚪")
            lines.append(f"  {sev_icon} {icon} [{label}] {a.skill_name}")
            lines.append(f"     原因: {a.reason}")
            lines.append(f"     健康分: {a.health_score:.1f}")
            if a.related_skills:
                lines.append(f"     关联: {', '.join(a.related_skills)}")
            lines.append("")

        # 统计
        deprecate = sum(1 for a in actions if a.action == "deprecate")
        remove = sum(1 for a in actions if a.action == "remove")
        merge = sum(1 for a in actions if a.action == "merge")

        lines.append("  ┌─────────────────────────────┐")
        lines.append(f"  │ 📉 建议淘汰: {deprecate:>3}            │")
        lines.append(f"  │ 🗑️  建议移除: {remove:>3}            │")
        lines.append(f"  │ 🔗 建议合并: {merge:>3} 对           │")
        lines.append("  └─────────────────────────────┘")

        if not dry_run:
            lines.append("")
            lines.append("  ⚠️  执行模式尚未实现，请手动处理以上建议")

        lines.append("=" * 60)

        report = "\n".join(lines)
        print(report)
        return report
