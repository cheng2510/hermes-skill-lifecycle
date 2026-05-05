"""
自动清理器

基于健康评分自动清理低质量技能，支持干运行模式。
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from .skill_registry import SkillRegistry, SkillMetadata, SkillTier

logger = logging.getLogger(__name__)


@dataclass
class PruneAction:
    """清理动作记录"""
    skill_name: str
    action: str  # deprecate, archive, remove
    reason: str
    health_score: float
    last_used: Optional[str] = None


class AutoPruner:
    """自动清理器"""

    # 默认配置
    DEFAULT_CONFIG = {
        'stale_days': 90,          # 超过多少天未使用视为过时
        'deprecate_threshold': 40,  # 健康分低于此值标记为废弃
        'remove_threshold': 20,     # 健康分低于此值建议删除
        'archive_before_remove': True,  # 删除前是否归档
        'archive_dir': '~/.hermes/archived_skills'  # 归档目录
    }

    def __init__(self, registry: SkillRegistry, config: Optional[Dict] = None):
        """
        初始化清理器

        Args:
            registry: 技能注册表
            config: 清理配置
        """
        self.registry = registry
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.actions: List[PruneAction] = []

    def analyze(self) -> List[PruneAction]:
        """
        分析技能，生成清理建议

        Returns:
            清理动作列表
        """
        self.actions = []
        self.registry.update_all_health_scores()

        for name, skill in self.registry.skills.items():
            action = self._analyze_skill(name, skill)
            if action:
                self.actions.append(action)

        logger.info(f"分析完成，建议 {len(self.actions)} 个清理动作")
        return self.actions

    def _analyze_skill(self, name: str, skill: SkillMetadata) -> Optional[PruneAction]:
        """
        分析单个技能

        Args:
            name: 技能名称
            skill: 技能元数据

        Returns:
            清理动作，不需要清理返回 None
        """
        # 检查是否过时
        if self._is_stale(skill):
            return PruneAction(
                skill_name=name,
                action='deprecate',
                reason=f"超过 {self.config['stale_days']} 天未使用",
                health_score=skill.health_score,
                last_used=str(skill.updated_at)
            )

        # 检查健康分是否低于移除阈值
        if skill.health_score < self.config['remove_threshold']:
            return PruneAction(
                skill_name=name,
                action='remove',
                reason=f"健康分 {skill.health_score} 低于移除阈值 {self.config['remove_threshold']}",
                health_score=skill.health_score
            )

        # 检查健康分是否低于废弃阈值
        if skill.health_score < self.config['deprecate_threshold']:
            return PruneAction(
                skill_name=name,
                action='deprecate',
                reason=f"健康分 {skill.health_score} 低于废弃阈值 {self.config['deprecate_threshold']}",
                health_score=skill.health_score
            )

        return None

    def _is_stale(self, skill: SkillMetadata) -> bool:
        """
        检查技能是否过时

        Args:
            skill: 技能元数据

        Returns:
            是否过时
        """
        if not skill.updated_at:
            return False

        stale_threshold = datetime.now() - timedelta(days=self.config['stale_days'])
        return skill.updated_at < stale_threshold

    def execute(self, dry_run: bool = True) -> Dict:
        """
        执行清理动作

        Args:
            dry_run: 是否为干运行模式

        Returns:
            执行结果
        """
        if not self.actions:
            self.analyze()

        results = {
            'total': len(self.actions),
            'executed': 0,
            'skipped': 0,
            'actions': []
        }

        for action in self.actions:
            if dry_run:
                results['actions'].append({
                    'skill': action.skill_name,
                    'action': action.action,
                    'reason': action.reason,
                    'status': 'dry_run'
                })
                logger.info(f"[DRY RUN] {action.skill_name}: {action.action} - {action.reason}")
            else:
                success = self._execute_action(action)
                results['actions'].append({
                    'skill': action.skill_name,
                    'action': action.action,
                    'reason': action.reason,
                    'status': 'executed' if success else 'failed'
                })
                if success:
                    results['executed'] += 1
                else:
                    results['skipped'] += 1

        return results

    def _execute_action(self, action: PruneAction) -> bool:
        """
        执行单个清理动作

        Args:
            action: 清理动作

        Returns:
            是否成功
        """
        skill_path = Path(self.registry.skills[action.skill_name].path)
        
        if not skill_path.exists():
            logger.warning(f"技能路径不存在: {skill_path}")
            return False

        try:
            if action.action == 'archive':
                return self._archive_skill(skill_path, action.skill_name)
            elif action.action == 'remove':
                if self.config['archive_before_remove']:
                    self._archive_skill(skill_path, action.skill_name)
                return self._remove_skill(skill_path, action.skill_name)
            elif action.action == 'deprecate':
                return self._mark_deprecated(skill_path, action.skill_name)
            else:
                logger.warning(f"未知动作: {action.action}")
                return False
        except Exception as e:
            logger.error(f"执行动作失败: {e}")
            return False

    def _archive_skill(self, skill_path: Path, skill_name: str) -> bool:
        """归档技能"""
        archive_dir = Path(os.path.expanduser(self.config['archive_dir']))
        archive_dir.mkdir(parents=True, exist_ok=True)

        archive_path = archive_dir / f"{skill_name}_{datetime.now().strftime('%Y%m%d')}"
        
        if archive_path.exists():
            archive_path = archive_dir / f"{skill_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        shutil.copytree(skill_path, archive_path)
        logger.info(f"技能 {skill_name} 已归档到 {archive_path}")
        return True

    def _remove_skill(self, skill_path: Path, skill_name: str) -> bool:
        """删除技能"""
        shutil.rmtree(skill_path)
        logger.info(f"技能 {skill_name} 已删除")
        return True

    def _mark_deprecated(self, skill_path: Path, skill_name: str) -> bool:
        """标记技能为废弃"""
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding='utf-8')
            
            # 在 frontmatter 中添加 deprecated 标记
            if 'deprecated:' not in content:
                content = content.replace(
                    '---\n',
                    '---\ndeprecated: true\n',
                    1
                )
                skill_md.write_text(content, encoding='utf-8')
                logger.info(f"技能 {skill_name} 已标记为废弃")
                return True
        
        return False

    def get_prune_report(self) -> Dict:
        """
        生成清理报告

        Returns:
            清理报告字典
        """
        if not self.actions:
            self.analyze()

        by_action = {}
        for action in self.actions:
            by_action.setdefault(action.action, []).append(action.skill_name)

        return {
            'total_actions': len(self.actions),
            'by_action': {k: len(v) for k, v in by_action.items()},
            'skills': {
                'deprecate': by_action.get('deprecate', []),
                'remove': by_action.get('remove', []),
                'archive': by_action.get('archive', [])
            },
            'details': [
                {
                    'skill': a.skill_name,
                    'action': a.action,
                    'reason': a.reason,
                    'health_score': a.health_score
                }
                for a in self.actions
            ]
        }

    def update_config(self, config: Dict):
        """更新配置"""
        self.config.update(config)
        logger.info(f"清理器配置已更新: {config}")
