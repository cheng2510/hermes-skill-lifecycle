"""
测试技能注册表
"""

import os
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.skill_registry import SkillRegistry, SkillMetadata, SkillTier


@pytest.fixture
def temp_skills_dir():
    """创建临时技能目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_skill(temp_skills_dir):
    """创建示例技能"""
    skill_dir = Path(temp_skills_dir) / "test-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
description: A test skill for unit testing
version: 1.0.0
author: test
tags:
  - test
  - example
triggers:
  - test
  - example
dependencies:
  - dep1
created_at: 2024-01-01T00:00:00
updated_at: 2024-01-15T00:00:00
---

# Test Skill

This is a test skill.
""", encoding='utf-8')
    
    return skill_dir


class TestSkillRegistry:
    """技能注册表测试"""

    def test_parse_skill_md(self, sample_skill):
        """测试解析 SKILL.md"""
        registry = SkillRegistry(str(sample_skill.parent))
        metadata = registry.parse_skill_md(sample_skill)
        
        assert metadata is not None
        assert metadata.name == "test-skill"
        assert metadata.description == "A test skill for unit testing"
        assert metadata.version == "1.0.0"
        assert metadata.author == "test"
        assert "test" in metadata.tags
        assert "example" in metadata.tags
        assert "test" in metadata.triggers

    def test_scan_skills(self, temp_skills_dir, sample_skill):
        """测试扫描技能目录"""
        registry = SkillRegistry(temp_skills_dir)
        skills = registry.scan_skills()
        
        assert len(skills) == 1
        assert "test-skill" in skills

    def test_health_score_no_usage(self, sample_skill):
        """测试无使用数据的健康评分"""
        registry = SkillRegistry(str(sample_skill.parent))
        registry.scan_skills()
        
        score = registry.calculate_health_score("test-skill")
        assert 0 <= score <= 100

    def test_health_score_with_usage(self, sample_skill):
        """测试有使用数据的健康评分"""
        registry = SkillRegistry(str(sample_skill.parent))
        registry.scan_skills()
        
        usage_data = {
            "test-skill": {
                "recent_count": 50,
                "total_count": 100,
                "success_count": 90,
                "last_used": datetime.now().isoformat()
            }
        }
        registry.update_usage_data(usage_data)
        
        score = registry.calculate_health_score("test-skill")
        assert score > 0

    def test_classify_tier(self, sample_skill):
        """测试技能分级"""
        registry = SkillRegistry(str(sample_skill.parent))
        registry.scan_skills()
        
        # 设置高健康分
        registry.skills["test-skill"].health_score = 85
        assert registry.classify_tier("test-skill") == SkillTier.CORE
        
        # 设置中等健康分
        registry.skills["test-skill"].health_score = 50
        assert registry.classify_tier("test-skill") == SkillTier.CANDIDATE
        
        # 设置低健康分
        registry.skills["test-skill"].health_score = 20
        assert registry.classify_tier("test-skill") == SkillTier.DEPRECATED

    def test_skill_report(self, sample_skill):
        """测试生成技能报告"""
        registry = SkillRegistry(str(sample_skill.parent))
        registry.scan_skills()
        
        report = registry.get_skill_report()
        
        assert "total_skills" in report
        assert "tier_distribution" in report
        assert "average_health" in report
        assert report["total_skills"] == 1

    def test_nonexistent_skill(self, temp_skills_dir):
        """测试不存在的技能"""
        registry = SkillRegistry(temp_skills_dir)
        registry.scan_skills()
        
        assert registry.get_skill("nonexistent") is None
        assert registry.calculate_health_score("nonexistent") == 0.0
        assert registry.classify_tier("nonexistent") == SkillTier.DEPRECATED
