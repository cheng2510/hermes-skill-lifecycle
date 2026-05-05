"""使用追踪器测试"""

import tempfile
import os
from datetime import datetime, timedelta
from src.usage_tracker import UsageTracker


def test_record_event():
    """记录事件"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        tracker = UsageTracker(db_path=db_path)
        tracker.record("test-skill", success=True, context="test")
        stats = tracker.get_stats(days=1)
        assert stats["total_calls"] >= 1
    finally:
        os.unlink(db_path)


def test_get_stats():
    """获取统计"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        tracker = UsageTracker(db_path=db_path)
        tracker.record("skill-a", success=True)
        tracker.record("skill-a", success=True)
        tracker.record("skill-b", success=False)

        stats = tracker.get_stats(days=30)
        assert stats["total_calls"] == 3
        assert len(stats["per_skill"]) == 2
    finally:
        os.unlink(db_path)


def test_stale_skills():
    """检测过期技能"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        tracker = UsageTracker(db_path=db_path)
        # 记录一个很久以前的使用
        import sqlite3
        conn = sqlite3.connect(db_path)
        old_time = (datetime.now() - timedelta(days=60)).isoformat()
        conn.execute(
            "INSERT INTO usage_events (skill_name, timestamp, success, context) VALUES (?, ?, ?, ?)",
            ("old-skill", old_time, 1, "")
        )
        conn.commit()
        conn.close()

        stale = tracker.get_stale_skills(threshold_days=30)
        assert "old-skill" in stale
    finally:
        os.unlink(db_path)


def test_format_stats():
    """格式化统计报告"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        tracker = UsageTracker(db_path=db_path)
        tracker.record("my-skill", success=True)
        report = tracker.format_stats(days=30)
        assert "my-skill" in report
        assert "技能使用统计" in report
    finally:
        os.unlink(db_path)
