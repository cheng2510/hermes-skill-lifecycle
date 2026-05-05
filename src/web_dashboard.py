"""
Web 仪表板

提供 Flask Web 界面，用于可视化技能管理数据。
"""

import os
import json
from flask import Flask, render_template_string, jsonify
from typing import Optional

from .skill_registry import SkillRegistry
from .conflict_detector import ConflictDetector
from .usage_tracker import UsageTracker
from .auto_pruner import AutoPruner


DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes 技能管理仪表板</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card h2 { color: #666; font-size: 14px; text-transform: uppercase; margin-bottom: 15px; }
        .stat { font-size: 36px; font-weight: bold; color: #333; }
        .stat-label { color: #999; font-size: 12px; }
        .tier-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        .tier { text-align: center; padding: 15px; border-radius: 8px; }
        .tier.core { background: #d4edda; color: #155724; }
        .tier.candidate { background: #fff3cd; color: #856404; }
        .tier.deprecated { background: #f8d7da; color: #721c24; }
        .tier .count { font-size: 24px; font-weight: bold; }
        .tier .label { font-size: 12px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
        th { color: #666; font-size: 12px; text-transform: uppercase; }
        .score { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
        .score.high { background: #d4edda; color: #155724; }
        .score.medium { background: #fff3cd; color: #856404; }
        .score.low { background: #f8d7da; color: #721c24; }
        .bar { height: 8px; background: #eee; border-radius: 4px; overflow: hidden; }
        .bar-fill { height: 100%; background: #4CAF50; border-radius: 4px; }
        .conflict { padding: 10px; margin: 5px 0; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 Hermes 技能管理仪表板</h1>
        
        <div class="grid">
            <div class="card">
                <h2>总览</h2>
                <div class="stat">{{ summary.total_skills }}</div>
                <div class="stat-label">技能总数</div>
                <div style="margin-top: 15px;">
                    <div class="stat-label">平均健康分</div>
                    <div class="stat">{{ "%.1f"|format(summary.average_health) }}</div>
                </div>
            </div>
            
            <div class="card">
                <h2>分级分布</h2>
                <div class="tier-grid">
                    <div class="tier core">
                        <div class="count">{{ summary.tier_distribution.get('core', 0) }}</div>
                        <div class="label">核心层</div>
                    </div>
                    <div class="tier candidate">
                        <div class="count">{{ summary.tier_distribution.get('candidate', 0) }}</div>
                        <div class="label">候选层</div>
                    </div>
                    <div class="tier deprecated">
                        <div class="count">{{ summary.tier_distribution.get('deprecated', 0) }}</div>
                        <div class="label">废弃层</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>使用统计</h2>
                <div class="stat">{{ usage.total_events }}</div>
                <div class="stat-label">总使用次数</div>
                <div style="margin-top: 15px;">
                    <div class="stat-label">活跃技能</div>
                    <div class="stat">{{ usage.unique_skills }}</div>
                </div>
            </div>
        </div>
        
        <div class="grid" style="margin-top: 20px;">
            <div class="card" style="grid-column: span 2;">
                <h2>技能列表</h2>
                <table>
                    <thead>
                        <tr>
                            <th>技能名称</th>
                            <th>版本</th>
                            <th>分级</th>
                            <th>健康分</th>
                            <th>标签</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for name, skill in skills.items() %}
                        <tr>
                            <td><strong>{{ name }}</strong></td>
                            <td>{{ skill.version }}</td>
                            <td>
                                <span class="score {{ skill.tier }}">{{ skill.tier }}</span>
                            </td>
                            <td>
                                <span class="score {{ 'high' if skill.health_score >= 80 else 'medium' if skill.health_score >= 40 else 'low' }}">
                                    {{ "%.1f"|format(skill.health_score) }}
                                </span>
                            </td>
                            <td>{{ skill.tags|join(', ') }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h2>冲突检测</h2>
                {% if conflicts.total_conflicts > 0 %}
                    {% for detail in conflicts.details %}
                    <div class="conflict">{{ detail }}</div>
                    {% endfor %}
                {% else %}
                    <p style="color: #155724;">✓ 未发现冲突</p>
                {% endif %}
            </div>
        </div>
        
        <div class="grid" style="margin-top: 20px;">
            <div class="card">
                <h2>清理建议</h2>
                {% if prune_actions.total_actions > 0 %}
                    <table>
                        <thead>
                            <tr>
                                <th>技能</th>
                                <th>动作</th>
                                <th>原因</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for detail in prune_actions.details %}
                            <tr>
                                <td>{{ detail.skill }}</td>
                                <td><span class="score low">{{ detail.action }}</span></td>
                                <td>{{ detail.reason }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p style="color: #155724;">✓ 无需清理</p>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
"""


def create_app(skills_dir: Optional[str] = None) -> Flask:
    """
    创建 Flask 应用

    Args:
        skills_dir: 技能目录路径

    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)

    @app.route('/')
    def index():
        """仪表板首页"""
        registry = SkillRegistry(skills_dir)
        usage_tracker = UsageTracker()
        conflict_detector = ConflictDetector()
        pruner = AutoPruner(registry)

        # 扫描技能
        registry.scan_skills()
        usage_data = usage_tracker.get_all_stats(30)
        registry.update_usage_data(usage_data)
        registry.update_all_health_scores()

        # 获取数据
        summary = registry.get_skill_report()
        usage_report = usage_tracker.get_usage_report()

        # 检测冲突
        conflict_detector.skills = registry.skills
        conflicts = conflict_detector.get_conflict_report()

        # 清理建议
        pruner.analyze()
        prune_report = pruner.get_prune_report()

        return render_template_string(
            DASHBOARD_TEMPLATE,
            summary=summary,
            skills=summary['skills'],
            usage=usage_report,
            conflicts=conflicts,
            prune_actions=prune_report
        )

    @app.route('/api/skills')
    def api_skills():
        """API: 获取所有技能"""
        registry = SkillRegistry(skills_dir)
        registry.scan_skills()
        registry.update_all_health_scores()
        return jsonify(registry.get_skill_report())

    @app.route('/api/conflicts')
    def api_conflicts():
        """API: 获取冲突信息"""
        registry = SkillRegistry(skills_dir)
        registry.scan_skills()
        detector = ConflictDetector(registry.skills)
        detector.detect_all()
        report = detector.get_conflict_report()
        # 转换 Conflict 对象为字典
        report['conflicts'] = [
            {
                'skill_a': c.skill_a,
                'skill_b': c.skill_b,
                'type': c.conflict_type,
                'score': c.score,
                'details': c.details
            }
            for c in report['conflicts']
        ]
        return jsonify(report)

    @app.route('/api/usage')
    def api_usage():
        """API: 获取使用统计"""
        tracker = UsageTracker()
        return jsonify(tracker.get_usage_report())

    @app.route('/api/prune')
    def api_prune():
        """API: 获取清理建议"""
        registry = SkillRegistry(skills_dir)
        usage_tracker = UsageTracker()
        registry.scan_skills()
        usage_data = usage_tracker.get_all_stats(30)
        registry.update_usage_data(usage_data)
        pruner = AutoPruner(registry)
        pruner.analyze()
        return jsonify(pruner.get_prune_report())

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
