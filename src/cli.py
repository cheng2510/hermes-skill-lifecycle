"""
CLI 入口

用法：
  python -m src.cli scan        # 全量扫描 + 健康报告
  python -m src.cli conflicts   # 冲突检测
  python -m src.cli stats       # 使用统计
  python -m src.cli prune       # 清理建议
  python -m src.cli all         # 全部报告
"""

import sys
import argparse
from .skill_registry import SkillRegistry
from .conflict_detector import ConflictDetector
from .usage_tracker import UsageTracker
from .auto_pruner import AutoPruner


def cmd_scan(args):
    """全量扫描 + 健康报告"""
    registry = SkillRegistry(skills_dir=args.skills_dir, db_path=args.db)
    registry.scan_all()
    registry.generate_report()

def cmd_conflicts(args):
    """冲突检测"""
    registry = SkillRegistry(skills_dir=args.skills_dir, db_path=args.db)
    registry.scan_all()
    detector = ConflictDetector()
    conflicts = detector.detect_all(registry.skills)
    detector.format_report(conflicts)

def cmd_stats(args):
    """使用统计"""
    tracker = UsageTracker(db_path=args.db)
    tracker.format_stats(days=args.days)

def cmd_prune(args):
    """清理建议"""
    registry = SkillRegistry(skills_dir=args.skills_dir, db_path=args.db)
    registry.scan_all()
    pruner = AutoPruner(registry)
    actions = pruner.analyze()
    pruner.format_report(actions, dry_run=not args.execute)

def cmd_all(args):
    """全部报告"""
    print()
    cmd_scan(args)
    print()
    cmd_conflicts(args)
    print()
    cmd_stats(args)
    print()
    cmd_prune(args)

def cmd_record(args):
    """记录一次技能使用（供外部调用）"""
    tracker = UsageTracker(db_path=args.db)
    tracker.record(args.name, success=not args.failed, context=args.context or "")
    print(f"✅ 已记录: {args.name} ({'失败' if args.failed else '成功'})")

def main():
    parser = argparse.ArgumentParser(
        description="Hermes Agent 技能生命周期管理器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m src.cli scan                    # 扫描所有技能
  python -m src.cli conflicts               # 检测冲突
  python -m src.cli stats --days 7          # 最近7天统计
  python -m src.cli prune --dry-run         # 清理建议
  python -m src.cli record my-skill         # 记录使用
  python -m src.cli record my-skill --failed # 记录失败
  python -m src.cli all                     # 全部报告
        """
    )

    parser.add_argument("--skills-dir", default=None, help="技能目录路径 (默认 ~/.hermes/skills)")
    parser.add_argument("--db", default=None, help="SQLite 数据库路径 (默认 ~/.hermes/skill_lifecycle.db)")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # scan
    subparsers.add_parser("scan", help="全量扫描 + 健康报告")

    # conflicts
    subparsers.add_parser("conflicts", help="冲突检测")

    # stats
    p_stats = subparsers.add_parser("stats", help="使用统计")
    p_stats.add_argument("--days", type=int, default=30, help="统计天数 (默认30)")

    # prune
    p_prune = subparsers.add_parser("prune", help="清理建议")
    p_prune.add_argument("--execute", action="store_true", help="执行清理（默认 dry-run）")

    # record
    p_record = subparsers.add_parser("record", help="记录技能使用")
    p_record.add_argument("name", help="技能名称")
    p_record.add_argument("--failed", action="store_true", help="标记为失败")
    p_record.add_argument("--context", default="", help="调用上下文")

    # all
    subparsers.add_parser("all", help="全部报告")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "scan": cmd_scan,
        "conflicts": cmd_conflicts,
        "stats": cmd_stats,
        "prune": cmd_prune,
        "record": cmd_record,
        "all": cmd_all,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
