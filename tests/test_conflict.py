"""
测试冲突检测器
"""

import pytest
from src.conflict_detector import ConflictDetector, Conflict
from src.skill_registry import SkillMetadata


@pytest.fixture
def sample_skills():
    """创建示例技能集合"""
    return {
        "python-helper": SkillMetadata(
            name="python-helper",
            description="Help with Python programming tasks",
            tags=["python", "programming", "helper"],
            triggers=["python", "code", "help"]
        ),
        "python-assistant": SkillMetadata(
            name="python-assistant",
            description="Assist with Python development",
            tags=["python", "development", "assistant"],
            triggers=["python", "develop", "assist"]
        ),
        "java-helper": SkillMetadata(
            name="java-helper",
            description="Help with Java programming",
            tags=["java", "programming"],
            triggers=["java", "code"]
        ),
        "web-scraper": SkillMetadata(
            name="web-scraper",
            description="Scrape web pages for data extraction",
            tags=["web", "scraping", "data"],
            triggers=["scrape", "extract"]
        )
    }


class TestConflictDetector:
    """冲突检测器测试"""

    def test_no_conflicts(self):
        """测试无冲突情况"""
        skills = {
            "skill-a": SkillMetadata(
                name="skill-a",
                description="Unique description A",
                tags=["unique-tag-a"],
                triggers=["unique-trigger-a"]
            ),
            "skill-b": SkillMetadata(
                name="skill-b",
                description="Unique description B",
                tags=["unique-tag-b"],
                triggers=["unique-trigger-b"]
            )
        }
        
        detector = ConflictDetector(skills)
        conflicts = detector.detect_all()
        
        assert len(conflicts) == 0

    def test_name_similarity(self, sample_skills):
        """测试名称相似度检测"""
        detector = ConflictDetector(sample_skills)
        conflicts = detector.detect_all()
        
        # python-helper 和 python-assistant 应该被检测到
        name_conflicts = [c for c in conflicts if c.conflict_type == 'name_similarity']
        assert len(name_conflicts) > 0
        
        # 检查是否包含 python-helper 和 python-assistant
        conflict_pairs = [(c.skill_a, c.skill_b) for c in name_conflicts]
        assert ('python-helper', 'python-assistant') in conflict_pairs or \
               ('python-assistant', 'python-helper') in conflict_pairs

    def test_tag_collision(self, sample_skills):
        """测试标签碰撞检测"""
        detector = ConflictDetector(sample_skills)
        conflicts = detector.detect_all()
        
        tag_conflicts = [c for c in conflicts if c.conflict_type == 'tag_collision']
        
        # python-helper 和 python-assistant 共享 "python" 标签
        # python-helper 和 java-helper 共享 "programming" 标签
        assert len(tag_conflicts) > 0

    def test_trigger_conflict(self, sample_skills):
        """测试触发词冲突检测"""
        detector = ConflictDetector(sample_skills)
        conflicts = detector.detect_all()
        
        trigger_conflicts = [c for c in conflicts if c.conflict_type == 'trigger_conflict']
        
        # python-helper 和 python-assistant 都有 "python" 触发词
        # python-helper 和 java-helper 都有 "code" 触发词
        assert len(trigger_conflicts) > 0

    def test_description_overlap(self):
        """测试描述重叠检测"""
        skills = {
            "skill-a": SkillMetadata(
                name="skill-a",
                description="A tool for processing data files",
                tags=[],
                triggers=[]
            ),
            "skill-b": SkillMetadata(
                name="skill-b",
                description="A tool for processing data",
                tags=[],
                triggers=[]
            )
        }
        
        detector = ConflictDetector(skills)
        conflicts = detector.detect_all()
        
        desc_conflicts = [c for c in conflicts if c.conflict_type == 'description_overlap']
        assert len(desc_conflicts) > 0

    def test_levenshtein_similarity(self):
        """测试 Levenshtein 相似度计算"""
        # 相同字符串
        assert ConflictDetector._levenshtein_similarity("test", "test") == 1.0
        
        # 完全不同
        similarity = ConflictDetector._levenshtein_similarity("abc", "xyz")
        assert similarity < 0.5
        
        # 相似字符串
        similarity = ConflictDetector._levenshtein_similarity("python-helper", "python-assistant")
        assert similarity > 0.3

    def test_tfidf_cosine_similarity(self):
        """测试 TF-IDF 余弦相似度"""
        # 相同文本
        similarity = ConflictDetector._tfidf_cosine_similarity(
            "Python programming helper",
            "Python programming helper"
        )
        assert similarity == 1.0
        
        # 完全不同
        similarity = ConflictDetector._tfidf_cosine_similarity(
            "Python programming",
            "Java development"
        )
        assert similarity == 0.0
        
        # 部分重叠
        similarity = ConflictDetector._tfidf_cosine_similarity(
            "Python programming helper",
            "Python development tool"
        )
        assert 0 < similarity < 1

    def test_conflict_report(self, sample_skills):
        """测试冲突报告生成"""
        detector = ConflictDetector(sample_skills)
        detector.detect_all()
        
        report = detector.get_conflict_report()
        
        assert "total_conflicts" in report
        assert "by_type" in report
        assert "details" in report
        assert report["total_conflicts"] > 0

    def test_get_skill_conflicts(self, sample_skills):
        """测试获取特定技能的冲突"""
        detector = ConflictDetector(sample_skills)
        detector.detect_all()
        
        conflicts = detector.get_skill_conflicts("python-helper")
        assert len(conflicts) > 0
        
        # 所有冲突都应该包含 python-helper
        for c in conflicts:
            assert c.skill_a == "python-helper" or c.skill_b == "python-helper"
