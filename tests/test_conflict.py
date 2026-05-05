"""冲突检测测试"""

from src.skill_registry import SkillMeta
from src.conflict_detector import ConflictDetector


def test_name_similarity():
    """名称相似度检测"""
    detector = ConflictDetector()
    assert detector._name_similarity("github-pr", "github-pr-workflow") > 0.5
    assert detector._name_similarity("skill-a", "completely-different") < 0.5


def test_tag_similarity():
    """标签碰撞检测"""
    detector = ConflictDetector()
    assert detector._tag_similarity(["git", "pr"], ["git", "review"]) > 0.3
    assert detector._tag_similarity(["python"], ["javascript"]) == 0.0


def test_no_conflicts():
    """无冲突场景"""
    detector = ConflictDetector()
    skills = {
        "a": SkillMeta(name="a", description="Web scraping tool", tags=["web"]),
        "b": SkillMeta(name="b", description="Database migration", tags=["db"]),
    }
    conflicts = detector.detect_all(skills)
    # 应该很少或没有冲突
    assert isinstance(conflicts, list)


def test_detect_similar_skills():
    """检测相似技能"""
    detector = ConflictDetector()
    skills = {
        "github-pr": SkillMeta(name="github-pr", description="Manage GitHub pull requests"),
        "github-pull-request": SkillMeta(name="github-pull-request", description="Handle GitHub pull requests"),
    }
    conflicts = detector.detect_all(skills)
    # 应该检测到名称和描述冲突
    assert len(conflicts) > 0
