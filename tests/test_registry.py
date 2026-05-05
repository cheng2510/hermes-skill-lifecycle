"""技能注册表测试"""

import tempfile
import os
from pathlib import Path
from src.skill_registry import SkillRegistry


def create_test_skill(dir_path: Path, name: str, category: str = "test"):
    """创建测试技能文件"""
    skill_dir = dir_path / category / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"""---
name: {name}
description: Test skill for {name}
version: 1.0.0
author: test
metadata:
  hermes:
    tags: [test, {name}]
    related_skills: []
---

## When to Use
- Use when testing {name}

## Common Pitfalls
1. This is a test
"""
    (skill_dir / "SKILL.md").write_text(content)


def test_scan_empty_dir():
    """空目录扫描"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = SkillRegistry(skills_dir=tmpdir)
        skills = registry.scan_all()
        assert len(skills) == 0


def test_scan_single_skill():
    """单技能扫描"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_skill(Path(tmpdir), "my-skill")
        registry = SkillRegistry(skills_dir=tmpdir)
        skills = registry.scan_all()
        assert len(skills) == 1
        assert "my-skill" in skills
        assert skills["my-skill"].description == "Test skill for my-skill"


def test_scan_multiple_skills():
    """多技能扫描"""
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in ["skill-a", "skill-b", "skill-c"]:
            create_test_skill(Path(tmpdir), name)
        registry = SkillRegistry(skills_dir=tmpdir)
        skills = registry.scan_all()
        assert len(skills) == 3


def test_health_scoring():
    """健康度评分"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_skill(Path(tmpdir), "test-skill")
        registry = SkillRegistry(skills_dir=tmpdir)
        registry.scan_all()
        skill = registry.get_skill("test-skill")
        assert skill is not None
        assert 0 <= skill.health_score <= 100


def test_tier_classification():
    """层级分类"""
    registry = SkillRegistry()
    assert registry._classify_tier(90) == "core"
    assert registry._classify_tier(70) == "candidate"
    assert registry._classify_tier(50) == "watch"
    assert registry._classify_tier(20) == "deprecated"
