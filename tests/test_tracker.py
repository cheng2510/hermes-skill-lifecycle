"""
测试使用追踪器
"""

import os
import pytest
import tempfile
from datetime import datetime, timedelta

from src.usage_tracker import UsageTracker, UsageEvent


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_usage.db")
        yield db_path


@pytest.fixture
def tracker(temp_db):
    """创建使用追踪器实例"""
    return UsageTracker(temp_db)


@pytest.fixture
def sample_events(tracker):
    """创建示例使用事件"""
    events = [
        UsageEvent(
            skill_name="test-skill",
            timestamp=datetime.now() - timedelta(days=i),
            success=i % 3 != 0,  # 每3次失败1次
            duration_ms=100 + i * 10,
            context=f"context-{i}"
        )
        for i in range(10)
    ]
    
    for event in events:
        tracker.record_event(event)
    
    return events


class TestUsageTracker:
    """使用追踪器测试"""

    def test_record_event(self, tracker):
        """测试记录使用事件"""
        event = UsageEvent(
            skill_name="test-skill",
            timestamp=datetime.now(),
            success=True,
            duration_ms=150,
            context="test context"
        )
        
        tracker.record_event(event)
        
        stats = tracker.get_skill_stats("test-skill", days=7)
        assert stats['recent_count'] == 1
        assert stats['success_count'] == 1

    def test_get_skill_stats(self, tracker, sample_events):
        """测试获取技能统计"""
        stats = tracker.get_skill_stats("test-skill", days=30)
        
        assert stats['recent_count'] == 10
        assert stats['success_count'] == 7  # 10 个事件中 7 个成功
        assert stats['last_used'] is not None
        assert stats['avg_duration_ms'] > 0

    def test_get_all_stats(self, tracker, sample_events):
        """测试获取所有技能统计"""
        # 添加另一个技能的事件
        event = UsageEvent(
            skill_name="another-skill",
            timestamp=datetime.now(),
            success=True,
            duration_ms=200
        )
        tracker.record_event(event)
        
        stats = tracker.get_all_stats(30)
        
        assert len(stats) == 2
        assert "test-skill" in stats
        assert "another-skill" in stats

    def test_get_daily_stats(self, tracker, sample_events):
        """测试获取每日统计"""
        daily = tracker.get_daily_stats("test-skill", days=30)
        
        assert len(daily) > 0
        for d in daily:
            assert 'date' in d
            assert 'count' in d
            assert 'success' in d

    def test_get_weekly_stats(self, tracker, sample_events):
        """测试获取每周统计"""
        weekly = tracker.get_weekly_stats("test-skill", weeks=4)
        
        assert len(weekly) > 0
        for w in weekly:
            assert 'week' in w
            assert 'count' in w
            assert 'success' in w

    def test_analyze_trend_increasing(self, tracker):
        """测试增长趋势分析"""
        # 创建增长趋势数据
        for i in range(14):
            event = UsageEvent(
                skill_name="growing-skill",
                timestamp=datetime.now() - timedelta(days=13 - i),
                success=True,
                duration_ms=100
            )
            tracker.record_event(event)
        
        # 后半段添加更多事件
        for i in range(10):
            event = UsageEvent(
                skill_name="growing-skill",
                timestamp=datetime.now() - timedelta(hours=i),
                success=True,
                duration_ms=100
            )
            tracker.record_event(event)
        
        trend = tracker.analyze_trend("growing-skill", days=14)
        
        assert trend['trend'] == 'active'
        assert trend['direction'] == 'increasing'

    def test_analyze_trend_decreasing(self, tracker):
        """测试下降趋势分析"""
        # 前半段添加更多事件
        for i in range(10):
            event = UsageEvent(
                skill_name="declining-skill",
                timestamp=datetime.now() - timedelta(days=13, hours=i),
                success=True,
                duration_ms=100
            )
            tracker.record_event(event)
        
        # 后半段只有少量事件
        event = UsageEvent(
            skill_name="declining-skill",
            timestamp=datetime.now() - timedelta(days=1),
            success=True,
            duration_ms=100
        )
        tracker.record_event(event)
        
        trend = tracker.analyze_trend("declining-skill", days=14)
        
        assert trend['trend'] == 'active'
        assert trend['direction'] == 'decreasing'

    def test_analyze_trend_insufficient_data(self, tracker):
        """测试数据不足的趋势分析"""
        event = UsageEvent(
            skill_name="new-skill",
            timestamp=datetime.now(),
            success=True,
            duration_ms=100
        )
        tracker.record_event(event)
        
        trend = tracker.analyze_trend("new-skill", days=30)
        
        assert trend['trend'] == 'insufficient_data'

    def test_get_usage_report(self, tracker, sample_events):
        """测试生成使用报告"""
        report = tracker.get_usage_report()
        
        assert 'total_events' in report
        assert 'unique_skills' in report
        assert 'skill_stats' in report
        assert report['total_events'] == 10
        assert report['unique_skills'] == 1

    def test_cleanup_old_events(self, tracker):
        """测试清理旧事件"""
        # 添加旧事件
        old_event = UsageEvent(
            skill_name="old-skill",
            timestamp=datetime.now() - timedelta(days=100),
            success=True,
            duration_ms=100
        )
        tracker.record_event(old_event)
        
        # 添加新事件
        new_event = UsageEvent(
            skill_name="old-skill",
            timestamp=datetime.now(),
            success=True,
            duration_ms=100
        )
        tracker.record_event(new_event)
        
        # 清理 90 天前的事件
        tracker.cleanup_old_events(days=90)
        
        stats = tracker.get_skill_stats("old-skill", days=365)
        assert stats['recent_count'] == 1  # 只剩下新事件
