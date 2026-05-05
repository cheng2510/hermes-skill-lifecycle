"""
Web 仪表盘（可选）

启动：python -m src.web_dashboard
访问：http://localhost:5555
"""

import sys

try:
    from flask import Flask, jsonify, render_template_string
except ImportError:
    print("[!] 需要安装 flask: pip install flask")
    sys.exit(1)
from .skill_registry import SkillRegistry
from .conflict_detector import ConflictDetector
from .usage_tracker import UsageTracker
from .auto_pruner import AutoPruner

app = Flask(__name__)
registry = SkillRegistry()
tracker = UsageTracker()
detector = ConflictDetector()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Hermes Skill Lifecycle Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #58a6ff; margin-bottom: 20px; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
        .card h3 { color: #8b949e; font-size: 14px; margin-bottom: 8px; }
        .card .value { font-size: 32px; font-weight: bold; color: #58a6ff; }
        .card .sub { font-size: 12px; color: #8b949e; margin-top: 4px; }
        table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #30363d; }
        th { background: #21262d; color: #8b949e; font-weight: 600; }
        .tier-core { color: #3fb950; }
        .tier-candidate { color: #58a6ff; }
        .tier-watch { color: #d29922; }
        .tier-deprecated { color: #f85149; }
        .bar { display: inline-block; height: 16px; border-radius: 4px; min-width: 4px; }
        .bar-bg { background: #21262d; width: 100px; height: 16px; border-radius: 4px; display: inline-block; }
        .refresh { background: #238636; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
        .refresh:hover { background: #2ea043; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 Hermes Skill Lifecycle Dashboard</h1>
        <button class="refresh" onclick="location.reload()">🔄 刷新</button>
        <div id="content">加载中...</div>
    </div>
    <script>
        async function loadData() {
            const [health, conflicts, stats] = await Promise.all([
                fetch('/api/health').then(r => r.json()),
                fetch('/api/conflicts').then(r => r.json()),
                fetch('/api/stats').then(r => r.json()),
            ]);

            let html = '<div class="cards">';
            html += `<div class="card"><h3>技能总数</h3><div class="value">${health.total}</div></div>`;
            html += `<div class="card"><h3>核心技能</h3><div class="value tier-core">${health.tiers.core || 0}</div></div>`;
            html += `<div class="card"><h3>候选技能</h3><div class="value tier-candidate">${health.tiers.candidate || 0}</div></div>`;
            html += `<div class="card"><h3>待淘汰</h3><div class="value tier-deprecated">${health.tiers.deprecated || 0}</div></div>`;
            html += `<div class="card"><h3>冲突数</h3><div class="value">${conflicts.count}</div></div>`;
            html += `<div class="card"><h3>30天调用</h3><div class="value">${stats.total_calls}</div></div>`;
            html += '</div>';

            // 技能列表
            html += '<table><tr><th>技能</th><th>层级</th><th>健康分</th><th>30天调用</th><th>成功率</th></tr>';
            for (const s of health.skills) {
                const tierClass = 'tier-' + s.tier;
                const barWidth = Math.round(s.health_score);
                html += `<tr>
                    <td>${s.name}</td>
                    <td class="${tierClass}">${s.tier}</td>
                    <td><div class="bar-bg"><div class="bar" style="width:${barWidth}px;background:${s.health_score>=80?'#3fb950':s.health_score>=60?'#58a6ff':s.health_score>=40?'#d29922':'#f85149'}"></div></div> ${s.health_score}</td>
                    <td>${s.usage_count_30d}</td>
                    <td>${(s.success_rate*100).toFixed(0)}%</td>
                </tr>`;
            }
            html += '</table>';

            document.getElementById('content').innerHTML = html;
        }
        loadData();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/health")
def api_health():
    registry.scan_all()
    tiers = {}
    for s in registry.skills.values():
        tiers[s.tier] = tiers.get(s.tier, 0) + 1
    return jsonify({
        "total": len(registry.skills),
        "tiers": tiers,
        "skills": [
            {
                "name": s.name,
                "health_score": s.health_score,
                "tier": s.tier,
                "usage_count_30d": s.usage_count_30d,
                "success_rate": s.success_rate,
            }
            for s in sorted(registry.skills.values(), key=lambda x: x.health_score, reverse=True)
        ]
    })

@app.route("/api/conflicts")
def api_conflicts():
    registry.scan_all()
    conflicts = detector.detect_all(registry.skills)
    return jsonify({
        "count": len(conflicts),
        "conflicts": [
            {
                "skill_a": c.skill_a,
                "skill_b": c.skill_b,
                "type": c.conflict_type,
                "severity": c.severity,
                "score": c.score,
            }
            for c in conflicts
        ]
    })

@app.route("/api/stats")
def api_stats():
    return jsonify(tracker.get_stats())

def main():
    print("🧬 Hermes Skill Lifecycle Dashboard")
    print("   访问 http://localhost:5555")
    app.run(host="0.0.0.0", port=5555, debug=False)

if __name__ == "__main__":
    main()
