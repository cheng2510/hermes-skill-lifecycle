"""
冲突检测器

检测技能之间的冲突，包括：
- 名称相似度 (Levenshtein 编辑距离)
- 描述重叠 (TF-IDF 余弦相似度)
- 标签碰撞检测
- 触发词冲突检测
"""

import logging
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Conflict:
    """冲突记录"""
    skill_a: str
    skill_b: str
    conflict_type: str  # name_similarity, description_overlap, tag_collision, trigger_conflict
    score: float        # 冲突分数 0-1
    details: str        # 冲突详情

    def __str__(self):
        return f"[{self.conflict_type}] {self.skill_a} <-> {self.skill_b}: {self.score:.2f} ({self.details})"


class ConflictDetector:
    """技能冲突检测器"""

    # 冲突阈值配置
    THRESHOLDS = {
        'name_similarity': 0.8,
        'description_overlap': 0.7,
        'tag_collision_ratio': 0.5,
        'trigger_conflict': 1.0  # 任何触发词冲突都报告
    }

    def __init__(self, skills: Dict = None):
        """
        初始化冲突检测器

        Args:
            skills: 技能元数据字典 {name: SkillMetadata}
        """
        self.skills = skills or {}
        self.conflicts: List[Conflict] = []

    def detect_all(self) -> List[Conflict]:
        """
        执行所有冲突检测

        Returns:
            检测到的冲突列表
        """
        self.conflicts = []

        skill_names = list(self.skills.keys())
        for i in range(len(skill_names)):
            for j in range(i + 1, len(skill_names)):
                name_a, name_b = skill_names[i], skill_names[j]
                skill_a = self.skills[name_a]
                skill_b = self.skills[name_b]

                # 检测各类冲突
                self._check_name_similarity(name_a, name_b)
                self._check_description_overlap(skill_a, skill_b)
                self._check_tag_collision(skill_a, skill_b)
                self._check_trigger_conflict(skill_a, skill_b)

        logger.info(f"共检测到 {len(self.conflicts)} 个冲突")
        return self.conflicts

    def _check_name_similarity(self, name_a: str, name_b: str):
        """
        检测名称相似度

        使用 Levenshtein 编辑距离计算相似度
        """
        similarity = self._levenshtein_similarity(name_a, name_b)
        if similarity >= self.THRESHOLDS['name_similarity']:
            self.conflicts.append(Conflict(
                skill_a=name_a,
                skill_b=name_b,
                conflict_type='name_similarity',
                score=similarity,
                details=f"名称相似度 {similarity:.2f}，可能为重复技能"
            ))

    def _check_description_overlap(self, skill_a, skill_b):
        """
        检测描述重叠

        使用 TF-IDF 向量化 + 余弦相似度
        """
        if not skill_a.description or not skill_b.description:
            return

        similarity = self._tfidf_cosine_similarity(skill_a.description, skill_b.description)
        if similarity >= self.THRESHOLDS['description_overlap']:
            self.conflicts.append(Conflict(
                skill_a=skill_a.name,
                skill_b=skill_b.name,
                conflict_type='description_overlap',
                score=similarity,
                details=f"描述重叠度 {similarity:.2f}，功能可能重复"
            ))

    def _check_tag_collision(self, skill_a, skill_b):
        """
        检测标签碰撞

        计算标签集合的 Jaccard 相似度
        """
        tags_a = set(skill_a.tags)
        tags_b = set(skill_b.tags)

        if not tags_a or not tags_b:
            return

        intersection = tags_a & tags_b
        union = tags_a | tags_b
        jaccard = len(intersection) / len(union) if union else 0

        if jaccard >= self.THRESHOLDS['tag_collision_ratio']:
            self.conflicts.append(Conflict(
                skill_a=skill_a.name,
                skill_b=skill_b.name,
                conflict_type='tag_collision',
                score=jaccard,
                details=f"标签重叠: {', '.join(intersection)}"
            ))

    def _check_trigger_conflict(self, skill_a, skill_b):
        """
        检测触发词冲突

        两个技能使用相同的触发词会导致歧义
        """
        triggers_a = set(skill_a.triggers)
        triggers_b = set(skill_b.triggers)

        if not triggers_a or not triggers_b:
            return

        conflicts = triggers_a & triggers_b
        if conflicts:
            self.conflicts.append(Conflict(
                skill_a=skill_a.name,
                skill_b=skill_b.name,
                conflict_type='trigger_conflict',
                score=1.0,
                details=f"冲突触发词: {', '.join(conflicts)}"
            ))

    @staticmethod
    def _levenshtein_similarity(s1: str, s2: str) -> float:
        """
        计算 Levenshtein 相似度

        Args:
            s1, s2: 待比较的字符串

        Returns:
            相似度分数 0-1
        """
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0

        # 计算编辑距离
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,
                    matrix[i][j-1] + 1,
                    matrix[i-1][j-1] + cost
                )

        distance = matrix[len1][len2]
        max_len = max(len1, len2)
        return 1.0 - (distance / max_len)

    @staticmethod
    def _tfidf_cosine_similarity(text1: str, text2: str) -> float:
        """
        计算 TF-IDF 余弦相似度

        简化版本：使用词袋模型计算
        """
        # 分词（简单实现：按空格和标点分割）
        import re
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))

        if not words1 or not words2:
            return 0.0

        # 计算 Jaccard 相似度作为近似
        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def get_conflict_report(self) -> Dict:
        """
        生成冲突报告

        Returns:
            包含冲突统计和详情的报告
        """
        by_type = defaultdict(list)
        for conflict in self.conflicts:
            by_type[conflict.conflict_type].append(conflict)

        return {
            'total_conflicts': len(self.conflicts),
            'by_type': {t: len(c) for t, c in by_type.items()},
            'details': [str(c) for c in self.conflicts],
            'conflicts': self.conflicts
        }

    def get_skill_conflicts(self, skill_name: str) -> List[Conflict]:
        """
        获取特定技能的所有冲突

        Args:
            skill_name: 技能名称

        Returns:
            该技能的冲突列表
        """
        return [c for c in self.conflicts if c.skill_a == skill_name or c.skill_b == skill_name]
