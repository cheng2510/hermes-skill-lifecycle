"""
测试自动清理器
"""

import os
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.skill_registry import SkillRegistry, SkillMetadata, SkillTier
from src.auto_pruner import AutoPruner, PruneAction


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def registry_with_skills(temp_dir):
    """创建包含技能的注册表"""
    # 创建技能目录
    skills_dir = Path(temp_dir) / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建健康技能
    healthy_dir = skills_dir / "healthy-skill"
    healthy_dir.mkdir(parents=True, exist_ok=True)
    (healthy_dir / "SKILL.md").write_text("""---
name: healthy-skill
description: A healthy skill
version: 1.0.0
tags:
  - test
triggers:
  - healthy
created_at: 2024-01-01T00:00:00
updated_at: 2024-01-15T00:00:00
---

# Healthy Skill
""", encoding='utf-8')
    
    # 创建过时技能
    stale_dir = skills_dir / "stale-skill"
    stale_dir.mkdir(parents=True, exist_ok=True)
    (stale_dir / "SKILL.md").write_text(f"""---
name: stale-skill
description: A stale skill
version: 1.0.0
tags:
  - test
triggers:
  - stale
created_at: 2024-01-01T00:00:00
updated_at: {(datetime.now() - timedelta(days=100)).isoformat()}
---

# Stale Skill
""", encoding='utf-8')
    
    # 创建低健康分技能
    low_dir = skills_dir / "low-health-skill"
    low_dir.mkdir(parents=True, exist_ok=True)
    (low_dir / "SKILL.md").write_text("""---
name: low-health-skill
description: A low health skill
version: 1.0.0
tags:
  - test
triggers:
  - low
created_at: 2024-01-01T00:00:00
updated_at: 2024-01-15T00:00:00
---

# Low Health Skill
""", encoding='utf-8')
    
    registry = SkillRegistry(str(skills_dir))
    registry.scan_skills()
    
    return registry


class TestAutoPruner:
    """自动清理器测试"""

    def test_analyze(self, registry_with_skills):
        """测试分析清理建议"""
        pruner = AutoPruner(registry_with_skills)
        
        # 设置不同的健康分
        registry_with_skills.skills["healthy-skill"].health_score = 90
        registry_with_skills.skills["stale-skill"].health_score = 85
        registry_with_skills.skills["low-health-skill"].health_score = 15
        
        actions = pruner.analyze()
        
        # stale-skill 应该被标记为过时
        stale_actions = [a for a in actions if a.skill_name == "stale-skill"]
        assert len(stale_actions) > 0
        assert stale_actions[0].action == "deprecate"
        
        # low-health-skill 应该被建议移除
        low_actions = [a for a in actions if a.skill_name == "low-health-skill"]
        assert len(low_actions) > 0
        assert low_actions[0].action == "remove"

    def test_analyze_no_actions(self, registry_with_skills):
        """测试无需清理的情况"""
        pruner = AutoPruner(registry_with_skills)
        
        # 设置所有技能为高健康分
        for skill in registry_with_skills.skills.values():
            skill.health_score = 90
            skill.updated_at = datetime.now()
        
        actions = pruner.analyze()
        assert len(actions) == 0

    def test_dry_run(self, registry_with_skills):
        """测试干运行模式"""
        pruner = AutoPruner(registry_with_skills)
        
        registry_with_skills.skills["low-health-skill"].health_score = 15
        
        pruner.analyze()
        results = pruner.execute(dry_run=True)
        
        assert results['total'] > 0
        for action in results['actions']:
            assert action['status'] == 'dry_run'

    def test_execute_deprecate(self, registry_with_skills, temp_dir):
        """测试执行废弃动作"""
        pruner = AutoPruner(registry_with_skills)
        
        # 设置过时技能
        registry_with_skills.skills["stale-skill"].health_score = 85
        
        pruner.analyze()
        results = pruner.execute(dry_run=False)
        
        assert results['executed'] > 0
        
        # 检查 SKILL.md 是否被更新
        skill_md = Path(registry_with_skills.skills["stale-skill"].path) / "SKILL.md"
        content = skill_md.read_text(encoding='utf-8')
        assert 'deprecated: true' in content

    def test_execute_remove(self, registry_with_skills, temp_dir):
        """测试执行移除动作"""
        pruner = AutoPruner(registry_with_skills, config={
            'archive_before_remove': False  # 不归档直接删除
        })
        
        registry_with_skills.skills["low-health-skill"].health_score = 15
        
        pruner.analyze()
        results = pruner.execute(dry_run=False)
        
        assert results['executed'] > 0
        
        # 检查技能目录是否被删除
        skill_path = Path(registry_with_skills.skills["low-health-skill"].path)
        assert not skill_path.exists()

    def test_execute_archive(self, registry_with_skills, temp_dir):
        """测试执行归档动作"""
        archive_dir = Path(temp_dir) / "archive"
        
        pruner = AutoPruner(registry_with_skills, config={
            'archive_dir': str(archive_dir)
        })
        
        registry_with_skills.skills["low-health-skill"].health_score = 15
        
        pruner.analyze()
        results = pruner.execute(dry_run=False)
        
        assert results['executed'] > 0
        
        # 检查归档目录是否存在
        assert archive_dir.exists()

    def test_get_prune_report(self, registry_with_skills):
        """测试生成清理报告"""
        pruner = AutoPruner(registry_with_skills)
        
        registry_with_skills.skills["low-health-skill"].health_score = 15
        
        pruner.analyze()
        report = pruner.get_prune_report()
        
        assert 'total_actions' in report
        assert 'by_action' in report
        assert 'skills' in report
        assert 'details' in report
        assert report['total_actions'] > 0

    def test_update_config(self, registry_with_skills):
        """测试更新配置"""
        pruner = AutoPruner(registry_with_skills)
        
        new_config = {
            'stale_days': 60,
            'deprecate_threshold': 30
        }
        pruner.update_config(new_config)
        
        assert pruner.config['stale_days'] == 60
        assert pruner.config['deprecate_threshold'] == 30

    def test_custom_thresholds(self, registry_with_skills):
        """测试自定义阈值"""
        pruner = AutoPruner(registry_with_skills, config={
            'stale_days': 30,
            'deprecate_threshold': 50,
            'remove_threshold': 30
        })
        
        # 设置技能为中等健康分
        registry_with_skills.skills["healthy-skill"].health_score = 45
        
        actions = pruner.analyze()
        
        # 健康分 45 应该被废弃（阈值 50）
        healthy_actions = [a for a in actions if a.skill_name == "healthy-skill"]
        assert len(healthy_actions) > 0
        assert healthy_actions[0].action == "deprecate"
