"""
CLI 接口

提供命令行工具，包括：
- hermes-skills scan: 全面扫描技能生态系统
- hermes-skills health: 健康报告
- hermes-skills conflicts: 冲突检测
- hermes-skills prune: 清理建议
- hermes-skills stats: 使用统计
- hermes-skills dashboard: 启动 Web 仪表板
"""

import sys
import json
import logging
import click
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from .skill_registry import SkillRegistry, SkillTier
from .conflict_detector import ConflictDetector
from .usage_tracker import UsageTracker
from .auto_pruner import AutoPruner

console = Console()
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@click.group()
@click.option('--skills-dir', '-d', help='技能目录路径')
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
@click.pass_context
def cli(ctx, skills_dir, verbose):
    """Hermes Agent 技能生命周期管理工具"""
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj['skills_dir'] = skills_dir
    ctx.obj['verbose'] = verbose


@cli.command()
@click.pass_context
def scan(ctx):
    """全面扫描技能生态系统"""
    skills_dir = ctx.obj.get('skills_dir')
    registry = SkillRegistry(skills_dir)
    usage_tracker = UsageTracker()
    
    console.print("[bold blue]扫描技能生态系统...[/bold blue]")
    
    # 扫描技能
    skills = registry.scan_skills()
    console.print(f"发现 {len(skills)} 个技能")
    
    # 更新使用数据
    usage_data = usage_tracker.get_all_stats(30)
    registry.update_usage_data(usage_data)
    
    # 更新健康评分
    registry.update_all_health_scores()
    
    # 生成报告
    report = registry.get_skill_report()
    
    # 显示分级分布
    console.print("\n[bold]技能分级分布:[/bold]")
    tier_table = Table(show_header=True, header_style="bold magenta")
    tier_table.add_column("分级", style="cyan")
    tier_table.add_column("数量", justify="right")
    tier_table.add_column("百分比", justify="right")
    
    total = report['total_skills']
    for tier_name, count in report['tier_distribution'].items():
        pct = (count / total * 100) if total > 0 else 0
        tier_table.add_row(tier_name, str(count), f"{pct:.1f}%")
    
    console.print(tier_table)
    
    # 显示详细技能列表
    console.print("\n[bold]技能详情:[/bold]")
    detail_table = Table(show_header=True, header_style="bold magenta")
    detail_table.add_column("技能名称", style="cyan")
    detail_table.add_column("版本")
    detail_table.add_column("分级", style="green")
    detail_table.add_column("健康分", justify="right")
    detail_table.add_column("标签")
    
    for name, data in sorted(report['skills'].items()):
        tier_style = {
            'core': 'green',
            'candidate': 'yellow',
            'deprecated': 'red'
        }.get(data['tier'], 'white')
        
        detail_table.add_row(
            name,
            data.get('version', '-'),
            f"[{tier_style}]{data['tier']}[/{tier_style}]",
            f"{data['health_score']:.1f}",
            ', '.join(data.get('tags', []))
        )
    
    console.print(detail_table)
    console.print(f"\n平均健康分: [bold]{report['average_health']:.1f}[/bold]")


@cli.command()
@click.option('--skill', '-s', help='查看特定技能的健康详情')
@click.pass_context
def health(ctx, skill):
    """生成健康报告"""
    skills_dir = ctx.obj.get('skills_dir')
    registry = SkillRegistry(skills_dir)
    usage_tracker = UsageTracker()
    
    console.print("[bold blue]生成健康报告...[/bold blue]")
    
    # 扫描技能
    registry.scan_skills()
    usage_data = usage_tracker.get_all_stats(30)
    registry.update_usage_data(usage_data)
    registry.update_all_health_scores()
    
    if skill:
        # 显示特定技能详情
        skill_data = registry.get_skill(skill)
        if not skill_data:
            console.print(f"[red]技能 '{skill}' 不存在[/red]")
            return
        
        console.print(Panel(
            f"[bold]{skill_data.name}[/bold] v{skill_data.version}\n"
            f"描述: {skill_data.description}\n"
            f"分级: {skill_data.tier.value}\n"
            f"健康分: {skill_data.health_score:.1f}/100\n"
            f"标签: {', '.join(skill_data.tags)}\n"
            f"触发词: {', '.join(skill_data.triggers)}",
            title=f"技能详情: {skill}",
            border_style="blue"
        ))
        
        # 显示使用趋势
        trend = usage_tracker.analyze_trend(skill)
        console.print(f"\n[bold]使用趋势:[/bold]")
        console.print(f"  方向: {trend['direction']}")
        console.print(f"  变化率: {trend['change_rate']:.2%}")
    else:
        # 显示总体健康报告
        report = registry.get_skill_report()
        
        console.print(f"\n[bold]健康报告摘要[/bold]")
        console.print(f"总技能数: {report['total_skills']}")
        console.print(f"平均健康分: {report['average_health']:.1f}/100")
        
        # 按分级显示
        for tier in [SkillTier.CORE, SkillTier.CANDIDATE, SkillTier.DEPRECATED]:
            tier_skills = [name for name, data in report['skills'].items() if data['tier'] == tier.value]
            if tier_skills:
                style = {'core': 'green', 'candidate': 'yellow', 'deprecated': 'red'}[tier.value]
                console.print(f"\n[{style}]{tier.value.upper()} 层 ({len(tier_skills)} 个):[/{style}]")
                for name in tier_skills:
                    score = report['skills'][name]['health_score']
                    console.print(f"  - {name}: {score:.1f}")


@cli.command()
@click.pass_context
def conflicts(ctx):
    """检测技能冲突"""
    skills_dir = ctx.obj.get('skills_dir')
    registry = SkillRegistry(skills_dir)
    
    console.print("[bold blue]检测技能冲突...[/bold blue]")
    
    # 扫描技能
    registry.scan_skills()
    
    # 检测冲突
    detector = ConflictDetector(registry.skills)
    conflicts = detector.detect_all()
    report = detector.get_conflict_report()
    
    if not conflicts:
        console.print("[green]✓ 未发现冲突[/green]")
        return
    
    console.print(f"\n[bold]发现 {report['total_conflicts']} 个冲突:[/bold]")
    
    # 按类型显示
    for conflict_type, count in report['by_type'].items():
        console.print(f"\n[bold yellow]{conflict_type}[/bold yellow]: {count} 个")
        
        type_conflicts = [c for c in conflicts if c.conflict_type == conflict_type]
        for c in type_conflicts:
            console.print(f"  - {c.skill_a} <-> {c.skill_b}")
            console.print(f"    分数: {c.score:.2f}")
            console.print(f"    详情: {c.details}")


@cli.command()
@click.option('--dry-run', is_flag=True, default=True, help='干运行模式（默认）')
@click.option('--execute', is_flag=True, help='执行清理')
@click.pass_context
def prune(ctx, dry_run, execute):
    """清理建议和执行"""
    skills_dir = ctx.obj.get('skills_dir')
    registry = SkillRegistry(skills_dir)
    usage_tracker = UsageTracker()
    
    # 扫描技能
    registry.scan_skills()
    usage_data = usage_tracker.get_all_stats(30)
    registry.update_usage_data(usage_data)
    
    # 分析清理建议
    pruner = AutoPruner(registry)
    actions = pruner.analyze()
    report = pruner.get_prune_report()
    
    if not actions:
        console.print("[green]✓ 无需清理的技能[/green]")
        return
    
    console.print(f"[bold]清理建议 ({report['total_actions']} 个):[/bold]\n")
    
    # 显示建议
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("技能", style="cyan")
    table.add_column("动作", style="yellow")
    table.add_column("原因")
    table.add_column("健康分", justify="right")
    
    for detail in report['details']:
        action_style = {
            'deprecate': 'yellow',
            'remove': 'red',
            'archive': 'blue'
        }.get(detail['action'], 'white')
        
        table.add_row(
            detail['skill'],
            f"[{action_style}]{detail['action']}[/{action_style}]",
            detail['reason'],
            f"{detail['health_score']:.1f}"
        )
    
    console.print(table)
    
    # 执行清理
    if execute:
        console.print("\n[bold red]执行清理...[/bold red]")
        results = pruner.execute(dry_run=False)
        console.print(f"执行: {results['executed']}, 跳过: {results['skipped']}")
    else:
        console.print("\n[dim]提示: 使用 --execute 执行清理，当前为干运行模式[/dim]")


@cli.command()
@click.option('--skill', '-s', help='查看特定技能的统计')
@click.option('--days', '-d', default=30, help='统计天数')
@click.pass_context
def stats(ctx, skill, days):
    """使用统计"""
    usage_tracker = UsageTracker()
    
    if skill:
        # 显示特定技能统计
        skill_stats = usage_tracker.get_skill_stats(skill, days)
        trend = usage_tracker.analyze_trend(skill, days)
        
        console.print(Panel(
            f"[bold]{skill}[/bold]\n"
            f"使用次数: {skill_stats['recent_count']}\n"
            f"成功次数: {skill_stats['success_count']}\n"
            f"最后使用: {skill_stats['last_used'] or '从未使用'}\n"
            f"平均耗时: {skill_stats['avg_duration_ms']:.1f}ms\n"
            f"使用趋势: {trend['direction']} ({trend['change_rate']:.2%})",
            title=f"技能统计: {skill}",
            border_style="blue"
        ))
        
        # 显示每日统计
        daily = usage_tracker.get_daily_stats(skill, days)
        if daily:
            console.print(f"\n[bold]每日使用 ({len(daily)} 天):[/bold]")
            for d in daily[-10:]:  # 显示最近10天
                bar = '█' * d['count']
                console.print(f"  {d['date']}: {bar} ({d['count']})")
    else:
        # 显示总体统计
        report = usage_tracker.get_usage_report()
        
        console.print(f"[bold]使用统计摘要 ({days} 天)[/bold]\n")
        console.print(f"总事件数: {report['total_events']}")
        console.print(f"使用技能数: {report['unique_skills']}")
        
        if report['skill_stats']:
            console.print(f"\n[bold]技能使用排行:[/bold]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("技能", style="cyan")
            table.add_column("使用次数", justify="right")
            table.add_column("成功率", justify="right")
            table.add_column("最后使用")
            
            sorted_stats = sorted(
                report['skill_stats'].items(),
                key=lambda x: x[1]['recent_count'],
                reverse=True
            )
            
            for name, s in sorted_stats[:20]:
                success_rate = (s['success_count'] / s['recent_count'] * 100) if s['recent_count'] > 0 else 0
                table.add_row(
                    name,
                    str(s['recent_count']),
                    f"{success_rate:.1f}%",
                    s['last_used'] or '从未'
                )
            
            console.print(table)


@cli.command()
@click.option('--port', '-p', default=5000, help='Web 服务端口')
@click.option('--host', '-h', default='127.0.0.1', help='监听地址')
@click.pass_context
def dashboard(ctx, port, host):
    """启动 Web 仪表板"""
    from .web_dashboard import create_app
    
    console.print(f"[bold blue]启动 Web 仪表板...[/bold blue]")
    console.print(f"访问 http://{host}:{port}")
    
    app = create_app(ctx.obj.get('skills_dir'))
    app.run(host=host, port=port, debug=ctx.obj.get('verbose', False))


def main():
    """CLI 入口点"""
    cli(obj={})


if __name__ == '__main__':
    main()
