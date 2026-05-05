"""
使用追踪器 - SQLite 实现

记录技能使用事件，提供统计聚合和趋势分析功能。
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UsageEvent:
    """使用事件数据结构"""
    skill_name: str
    timestamp: datetime
    success: bool
    duration_ms: int = 0
    context: str = ""


class UsageTracker:
    """SQLite 使用追踪器"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化使用追踪器

        Args:
            db_path: SQLite 数据库路径，默认 ~/.hermes/data/usage.db
        """
        if db_path is None:
            db_path = str(Path.home() / ".hermes" / "data" / "usage.db")

        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_db(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    duration_ms INTEGER DEFAULT 0,
                    context TEXT DEFAULT ''
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_skill_name 
                ON usage_events(skill_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON usage_events(timestamp)
            """)

            conn.commit()

    def record_event(self, event: UsageEvent):
        """
        记录使用事件

        Args:
            event: 使用事件
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO usage_events (skill_name, timestamp, success, duration_ms, context) VALUES (?, ?, ?, ?, ?)",
                (
                    event.skill_name,
                    event.timestamp.isoformat(),
                    1 if event.success else 0,
                    event.duration_ms,
                    event.context
                )
            )
            conn.commit()

        logger.debug(f"记录使用事件: {event.skill_name} - {'成功' if event.success else '失败'}")

    def get_skill_stats(self, skill_name: str, days: int = 30) -> Dict:
        """
        获取技能使用统计

        Args:
            skill_name: 技能名称
            days: 统计天数

        Returns:
            统计数据字典
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # 总使用次数
            total = conn.execute(
                "SELECT COUNT(*) FROM usage_events WHERE skill_name = ? AND timestamp >= ?",
                (skill_name, cutoff)
            ).fetchone()[0]

            # 成功次数
            success = conn.execute(
                "SELECT COUNT(*) FROM usage_events WHERE skill_name = ? AND timestamp >= ? AND success = 1",
                (skill_name, cutoff)
            ).fetchone()[0]

            # 最后使用时间
            last_used = conn.execute(
                "SELECT MAX(timestamp) FROM usage_events WHERE skill_name = ?",
                (skill_name,)
            ).fetchone()[0]

            # 平均持续时间
            avg_duration = conn.execute(
                "SELECT AVG(duration_ms) FROM usage_events WHERE skill_name = ? AND timestamp >= ?",
                (skill_name, cutoff)
            ).fetchone()[0] or 0

        return {
            'recent_count': total,
            'total_count': total,
            'success_count': success,
            'last_used': last_used,
            'avg_duration_ms': round(avg_duration, 2)
        }

    def get_all_stats(self, days: int = 30) -> Dict[str, Dict]:
        """
        获取所有技能的使用统计

        Args:
            days: 统计天数

        Returns:
            技能名称到统计的映射
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT 
                    skill_name,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
                    MAX(timestamp) as last_used,
                    AVG(duration_ms) as avg_duration
                FROM usage_events 
                WHERE timestamp >= ?
                GROUP BY skill_name
            """, (cutoff,)).fetchall()

        stats = {}
        for row in rows:
            stats[row[0]] = {
                'recent_count': row[1],
                'total_count': row[1],
                'success_count': row[2],
                'last_used': row[3],
                'avg_duration_ms': round(row[4] or 0, 2)
            }

        return stats

    def get_daily_stats(self, skill_name: str, days: int = 30) -> List[Dict]:
        """
        获取每日使用统计

        Args:
            skill_name: 技能名称
            days: 统计天数

        Returns:
            每日统计列表
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success
                FROM usage_events 
                WHERE skill_name = ? AND timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            """, (skill_name, cutoff)).fetchall()

        return [{'date': row[0], 'count': row[1], 'success': row[2]} for row in rows]

    def get_weekly_stats(self, skill_name: str, weeks: int = 12) -> List[Dict]:
        """
        获取每周使用统计

        Args:
            skill_name: 技能名称
            weeks: 统计周数

        Returns:
            每周统计列表
        """
        cutoff = (datetime.now() - timedelta(weeks=weeks)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT 
                    strftime('%Y-W%W', timestamp) as week,
                    COUNT(*) as count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success
                FROM usage_events 
                WHERE skill_name = ? AND timestamp >= ?
                GROUP BY strftime('%Y-W%W', timestamp)
                ORDER BY week
            """, (skill_name, cutoff)).fetchall()

        return [{'week': row[0], 'count': row[1], 'success': row[2]} for row in rows]

    def analyze_trend(self, skill_name: str, days: int = 30) -> Dict:
        """
        分析使用趋势

        Args:
            skill_name: 技能名称
            days: 分析天数

        Returns:
            趋势分析结果
        """
        daily = self.get_daily_stats(skill_name, days)
        
        if len(daily) < 2:
            return {
                'trend': 'insufficient_data',
                'direction': 'stable',
                'change_rate': 0.0
            }

        # 计算前半段和后半段的平均使用量
        mid = len(daily) // 2
        first_half = sum(d['count'] for d in daily[:mid]) / max(1, mid)
        second_half = sum(d['count'] for d in daily[mid:]) / max(1, len(daily) - mid)

        if first_half == 0:
            change_rate = 1.0 if second_half > 0 else 0.0
        else:
            change_rate = (second_half - first_half) / first_half

        if change_rate > 0.2:
            direction = 'increasing'
        elif change_rate < -0.2:
            direction = 'decreasing'
        else:
            direction = 'stable'

        return {
            'trend': 'active',
            'direction': direction,
            'change_rate': round(change_rate, 2),
            'first_half_avg': round(first_half, 2),
            'second_half_avg': round(second_half, 2)
        }

    def get_usage_report(self) -> Dict:
        """
        生成使用报告

        Returns:
            使用报告字典
        """
        all_stats = self.get_all_stats(30)

        with sqlite3.connect(self.db_path) as conn:
            total_events = conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0]
            unique_skills = conn.execute("SELECT COUNT(DISTINCT skill_name) FROM usage_events").fetchone()[0]

        return {
            'total_events': total_events,
            'unique_skills': unique_skills,
            'skill_stats': all_stats
        }

    def cleanup_old_events(self, days: int = 90):
        """
        清理旧的使用事件

        Args:
            days: 保留天数
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM usage_events WHERE timestamp < ?",
                (cutoff,)
            )
            conn.commit()
            logger.info(f"清理了 {cursor.rowcount} 条旧记录")
