"""清理建议测试"""

import tempfile
from pathlib import Path
from src.skill_registry import SkillRegistry
from src.auto_pruner import AutoPruner


def test_empty_prune():
    """空技能库清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = SkillRegistry(skills_dir=tmpdir)
        registry.scan_all()
        pruner = AutoPruner(registry)
        actions = pruner.analyze()
        assert actions == []


def test_prune_low_health():
    """低健康度技能清理建议"""
    registry = SkillRegistry()
    # 模拟一个低健康度技能
    from src.skill_registry import SkillMeta
    skill = SkillMeta(
        name="old-skill",
        description="An old unused skill",
        health_score=15.0,
        tier="deprecated",
        usage_count_30d=0,
        success_rate=0.0,
        last_used_days_ago=200,
    )
    registry.skills = {"old-skill": skill}
    pruner = AutoPruner(registry)
    actions = pruner.analyze()
    assert len(actions) > 0
