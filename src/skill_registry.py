"""
技能注册表 - 核心模块

负责解析 SKILL.md 文件的 frontmatter，管理技能元数据，
计算健康评分，以及对技能进行分级分类。
"""

import os
import re
import json
import yaml
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SkillTier(Enum):
    """技能分级枚举"""
    CORE = "core"           # 核心层: 健康分 >= 80
    CANDIDATE = "candidate"  # 候选层: 40 <= 健康分 < 80
    DEPRECATED = "deprecated"  # 已废弃: 健康分 < 40


@dataclass
class SkillMetadata:
    """技能元数据结构"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tier: SkillTier = SkillTier.CANDIDATE
    health_score: float = 0.0
    path: str = ""

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = asdict(self)
        result['tier'] = self.tier.value
        if self.created_at:
            result['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            result['updated_at'] = self.updated_at.isoformat()
        return result


class SkillRegistry:
    """技能注册表核心类"""

    # 健康评分权重配置
    HEALTH_WEIGHTS = {
        'usage_frequency': 0.30,
        'success_rate': 0.25,
        'recency': 0.25,
        'dependency_quality': 0.20
    }

    # 分级阈值
    TIER_THRESHOLDS = {
        SkillTier.CORE: 80,
        SkillTier.CANDIDATE: 40,
        SkillTier.DEPRECATED: 0
    }

    def __init__(self, skills_dir: Optional[str] = None):
        """
        初始化技能注册表

        Args:
            skills_dir: 技能目录路径，默认 ~/.hermes/skills/
        """
        if skills_dir is None:
            skills_dir = os.path.expanduser("~/.hermes/skills")

        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, SkillMetadata] = {}
        self._usage_data: Dict[str, Dict] = {}

    def parse_skill_md(self, skill_path: Path) -> Optional[SkillMetadata]:
        """
        解析 SKILL.md 文件，提取 frontmatter 元数据

        Args:
            skill_path: 技能目录路径

        Returns:
            SkillMetadata 对象，解析失败返回 None
        """
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            logger.warning(f"技能目录 {skill_path} 缺少 SKILL.md 文件")
            return None

        try:
            content = skill_md.read_text(encoding='utf-8')
            return self._parse_frontmatter(content, skill_path)
        except Exception as e:
            logger.error(f"解析 {skill_md} 失败: {e}")
            return None

    def _parse_frontmatter(self, content: str, skill_path: Path) -> Optional[SkillMetadata]:
        """
        解析 Markdown frontmatter

        Args:
            content: SKILL.md 文件内容
            skill_path: 技能目录路径

        Returns:
            SkillMetadata 对象
        """
        # 匹配 YAML frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        
        if not frontmatter_match:
            logger.warning(f"技能 {skill_path.name} 的 SKILL.md 缺少 frontmatter")
            return SkillMetadata(
                name=skill_path.name,
                description="",
                path=str(skill_path)
            )

        try:
            metadata = yaml.safe_load(frontmatter_match.group(1))
            if not isinstance(metadata, dict):
                metadata = {}
        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误: {e}")
            metadata = {}

        return SkillMetadata(
            name=metadata.get('name', skill_path.name),
            description=metadata.get('description', ''),
            version=metadata.get('version', '1.0.0'),
            author=metadata.get('author', ''),
            tags=metadata.get('tags', []),
            triggers=metadata.get('triggers', []),
            dependencies=metadata.get('dependencies', []),
            created_at=self._parse_datetime(metadata.get('created_at')),
            updated_at=self._parse_datetime(metadata.get('updated_at')),
            path=str(skill_path)
        )

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """解析日期时间字符串"""
        if not dt_str:
            return None
        if isinstance(dt_str, datetime):
            return dt_str
        try:
            return datetime.fromisoformat(str(dt_str))
        except (ValueError, TypeError):
            return None

    def scan_skills(self) -> Dict[str, SkillMetadata]:
        """
        扫描技能目录，加载所有技能

        Returns:
            技能名称到元数据的映射字典
        """
        if not self.skills_dir.exists():
            logger.warning(f"技能目录不存在: {self.skills_dir}")
            return self.skills

        for item in self.skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                metadata = self.parse_skill_md(item)
                if metadata:
                    self.skills[metadata.name] = metadata
                    logger.info(f"加载技能: {metadata.name} v{metadata.version}")

        logger.info(f"共加载 {len(self.skills)} 个技能")
        return self.skills

    def update_usage_data(self, usage_data: Dict[str, Dict]):
        """
        更新使用数据，用于健康评分计算

        Args:
            usage_data: 技能使用数据字典
        """
        self._usage_data = usage_data

    def calculate_health_score(self, skill_name: str) -> float:
        """
        计算技能健康评分 (0-100)

        健康分 = (使用频率 × 0.30) + (成功率 × 0.25) + (新鲜度 × 0.25) + (依赖质量 × 0.20)

        Args:
            skill_name: 技能名称

        Returns:
            健康评分，0-100
        """
        if skill_name not in self.skills:
            return 0.0

        skill = self.skills[skill_name]
        usage = self._usage_data.get(skill_name, {})

        # 计算各维度分数
        usage_freq = self._calculate_usage_frequency(usage)
        success_rate = self._calculate_success_rate(usage)
        recency = self._calculate_recency_score(usage)
        dep_quality = self._calculate_dependency_quality(skill)

        # 加权计算总分
        score = (
            usage_freq * self.HEALTH_WEIGHTS['usage_frequency'] +
            success_rate * self.HEALTH_WEIGHTS['success_rate'] +
            recency * self.HEALTH_WEIGHTS['recency'] +
            dep_quality * self.HEALTH_WEIGHTS['dependency_quality']
        )

        skill.health_score = round(min(100.0, max(0.0, score)), 2)
        return skill.health_score

    def _calculate_usage_frequency(self, usage: Dict) -> float:
        """
        计算使用频率分数 (0-100)

        基于近30天使用次数归一化计算
        """
        recent_count = usage.get('recent_count', 0)
        # 使用对数缩放，100次以上为满分
        if recent_count <= 0:
            return 0.0
        return min(100.0, (recent_count / 100.0) * 100)

    def _calculate_success_rate(self, usage: Dict) -> float:
        """
        计算成功率分数 (0-100)

        成功率 = 成功执行次数 / 总执行次数
        """
        total = usage.get('total_count', 0)
        if total <= 0:
            return 50.0  # 无数据时给中等分数

        success = usage.get('success_count', 0)
        return (success / total) * 100

    def _calculate_recency_score(self, usage: Dict) -> float:
        """
        计算新鲜度分数 (0-100)

        使用指数衰减函数，最后使用时间越近分数越高
        """
        last_used = usage.get('last_used')
        if not last_used:
            return 30.0  # 无使用记录给较低分

        if isinstance(last_used, str):
            try:
                last_used = datetime.fromisoformat(last_used)
            except (ValueError, TypeError):
                return 30.0

        days_since = (datetime.now() - last_used).days
        # 指数衰减: 7天内满分，30天后降为约25分
        return max(0.0, 100.0 * (0.95 ** days_since))

    def _calculate_dependency_quality(self, skill: SkillMetadata) -> float:
        """
        计算依赖质量分数 (0-100)

        考虑依赖数量和依赖技能的健康度
        """
        deps = skill.dependencies
        if not deps:
            return 80.0  # 无依赖给较高分

        # 依赖数量惩罚: 超过5个依赖开始扣分
        count_penalty = max(0, (len(deps) - 5) * 10)

        # 依赖健康度: 计算依赖技能的平均健康分
        dep_scores = []
        for dep_name in deps:
            if dep_name in self.skills:
                dep_scores.append(self.skills[dep_name].health_score)

        avg_dep_score = sum(dep_scores) / len(dep_scores) if dep_scores else 50.0

        return max(0.0, avg_dep_score - count_penalty)

    def classify_tier(self, skill_name: str) -> SkillTier:
        """
        对技能进行分级分类

        Args:
            skill_name: 技能名称

        Returns:
            技能分级 (core/candidate/deprecated)
        """
        if skill_name not in self.skills:
            return SkillTier.DEPRECATED

        score = self.skills[skill_name].health_score

        if score >= self.TIER_THRESHOLDS[SkillTier.CORE]:
            return SkillTier.CORE
        elif score >= self.TIER_THRESHOLDS[SkillTier.CANDIDATE]:
            return SkillTier.CANDIDATE
        else:
            return SkillTier.DEPRECATED

    def update_all_health_scores(self):
        """更新所有技能的健康评分和分级"""
        for skill_name in self.skills:
            self.calculate_health_score(skill_name)
            tier = self.classify_tier(skill_name)
            self.skills[skill_name].tier = tier

    def get_skill_report(self) -> Dict:
        """
        生成技能报告

        Returns:
            包含统计信息的报告字典
        """
        self.update_all_health_scores()

        tiers = {t: [] for t in SkillTier}
        for name, skill in self.skills.items():
            tiers[skill.tier].append(name)

        return {
            'total_skills': len(self.skills),
            'tier_distribution': {t.value: len(n) for t, n in tiers.items()},
            'tier_skills': {t.value: n for t, n in tiers.items()},
            'skills': {name: skill.to_dict() for name, skill in self.skills.items()},
            'average_health': sum(s.health_score for s in self.skills.values()) / max(1, len(self.skills))
        }

    def export_metadata(self, output_path: str):
        """导出元数据到 JSON 文件"""
        report = self.get_skill_report()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"元数据已导出到 {output_path}")

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """获取技能元数据"""
        return self.skills.get(name)

    def list_skills(self, tier: Optional[SkillTier] = None) -> List[SkillMetadata]:
        """
        列出技能

        Args:
            tier: 可选的分级过滤

        Returns:
            技能列表
        """
        if tier:
            return [s for s in self.skills.values() if s.tier == tier]
        return list(self.skills.values())
