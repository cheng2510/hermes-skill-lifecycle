"""
技能使用追踪器

基于 SQLite 记录每次技能调用事件，提供统计分析。
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
import os


@dataclass
class UsageEvent:
    """使用事件"""
    skill_name: str
    timestamp: str
    success: bool
    context: str = ""  # 调用上下文（可选）


class UsageTracker:
    """使用追踪器"""

    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path or os.path.expanduser("~/.hermes/skill_lifecycle.db"))
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 1,
                context TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_name ON usage_events(skill_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_events(timestamp)
        """)
        conn.commit()
        conn.close()

    def record(self, skill_name: str, success: bool = True, context: str = ""):
        """记录一次技能使用"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usage_events (skill_name, timestamp, success, context) VALUES (?, ?, ?, ?)",
            (skill_name, datetime.now().isoformat(), int(success), context)
        )
        conn.commit()
        conn.close()

    def get_stats(self, days: int = 30) -> dict:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        since = (datetime.now() - timedelta(days=days)).isoformat()

        # 总调用次数
        cursor.execute("SELECT COUNT(*) FROM usage_events WHERE timestamp>=?", (since,))
        total = cursor.fetchone()[0]

        # 按技能统计
        cursor.execute("""
            SELECT skill_name,
                   COUNT(*) as total,
                   SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as ok,
                   MAX(timestamp) as last_used
            FROM usage_events
            WHERE timestamp>=?
            GROUP BY skill_name
            ORDER BY total DESC
        """, (since,))
        per_skill = []
        for row in cursor.fetchall():
            per_skill.append({
                "name": row[0],
                "total": row[1],
                "success": row[2],
                "success_rate": row[2] / row[1] if row[1] > 0 else 0,
                "last_used": row[3],
            })

        # 每日趋势
        cursor.execute("""
            SELECT DATE(timestamp) as day, COUNT(*) as cnt
            FROM usage_events
            WHERE timestamp>=?
            GROUP BY day
            ORDER BY day
        """, (since,))
        daily = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]

        conn.close()

        return {
            "period_days": days,
            "total_calls": total,
            "per_skill": per_skill,
            "daily_trend": daily,
        }

    def get_stale_skills(self, threshold_days: int = 30) -> list[str]:
        """获取长期未使用的技能"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=threshold_days)).isoformat()
        cursor.execute("""
            SELECT DISTINCT skill_name
            FROM usage_events
            WHERE skill_name NOT IN (
                SELECT DISTINCT skill_name
                FROM usage_events
                WHERE timestamp >= ?
            )
        """, (cutoff,))

        stale = [row[0] for row in cursor.fetchall()]
        conn.close()
        return stale

    def format_stats(self, days: int = 30) -> str:
        """格式化统计报告"""
        stats = self.get_stats(days)

        lines = []
        lines.append("=" * 60)
        lines.append(f"  技能使用统计（最近 {days} 天）")
        lines.append("=" * 60)
        lines.append(f"  总调用次数: {stats['total_calls']}")
        lines.append("")

        if stats["per_skill"]:
            lines.append(f"  {'技能名':<30} {'调用':>6} {'成功':>6} {'成功率':>8} {'最后使用':<12}")
            lines.append("  " + "-" * 70)
            for s in stats["per_skill"][:20]:
                last = s["last_used"][:10] if s["last_used"] else "从未"
                lines.append(
                    f"  {s['name']:<30} {s['total']:>6} {s['success']:>6} "
                    f"{s['success_rate']:>7.1%} {last:<12}"
                )
        else:
            lines.append("  暂无使用数据")

        lines.append("")
        lines.append("=" * 60)

        report = "\n".join(lines)
        print(report)
        return report
