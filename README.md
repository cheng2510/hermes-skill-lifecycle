# 🧬 Hermes Agent Skill Lifecycle Manager

> 解决 Hermes Agent 技能系统"只生不养"的系统性问题

## 问题背景

Hermes Agent 的 Skill 系统存在以下核心问题：

```
┌─────────────────────────────────────────────────────────┐
│                   当前 Skill 生态现状                      
├─────────────────────────────────────────────────────────
│  ❌ 技能只增不减 — 没有淘汰机制                             
│  ❌ 无使用追踪 — 不知道哪些技能有用                          
│  ❌ 无冲突检测 — 功能重叠的技能互相争抢                       
│  ❌ 无健康评估 — 坏掉的技能照样被加载                      
│  ❌ 无分层管理 — 89个技能平铺，核心技能被淹没              
└─────────────────────────────────────────────────────────┘
```

## 解决方案架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Skill Lifecycle Manager                      
├──────────┬──────────┬──────────┬──────────┬──────────────────
│ Registry │ Conflict │  Usage   │  Auto    │   Web Dashboard  
│  Engine  │ Detector │ Tracker  │  Pruner  │   (可选)         
├──────────┴──────────┴──────────┴──────────┴──────────────────
│                    SQLite 数据层                               
├──────────────────────────────────────────────────────────────
│              ~/.hermes/skills/ 文件系统                        
└──────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 技能健康度评分 (Skill Health Scoring)

基于多维度指标计算每个技能的健康分（0-100）：

| 指标 | 权重 | 说明 |
|------|------|------|
| 使用频率 | 30% | 最近30天被调用的次数 |
| 成功率 | 25% | 调用成功/总调用比 |
| 新鲜度 | 20% | 最后一次使用距今天数 |
| 依赖度 | 15% | 被其他技能引用的次数 |
| 文档完整度 | 10% | frontmatter 字段完整性和文档长度 |

### 2. 技能分层 (Skill Tiering)

```
┌─────────────┐
│  核心技能    │ ← 健康分 ≥ 80，高频使用
│  (Core)     │
├─────────────┤
│  候选技能    │ ← 健康分 60-79，有潜力
│ (Candidate) │
├─────────────┤
│  观察技能    │ ← 健康分 40-59，需要关注
│ (Watch)     │
├─────────────┤
│  待淘汰技能  │ ← 健康分 < 40，建议清理
│(Deprecated) │
└─────────────┘
```

### 3. 冲突检测 (Conflict Detection)

- **名称相似度**：Levenshtein 距离检测相似命名
- **描述重叠度**：TF-IDF 余弦相似度检测功能重复
- **标签碰撞**：检测 tag 集合的 Jaccard 相似度
- **触发词冲突**：检测 When to Use 部分的关键词重叠

### 4. 使用追踪 (Usage Tracking)

- SQLite 存储每次技能调用事件
- 统计聚合：日/周/月维度
- 趋势分析：识别上升/下降趋势

### 5. 自动清理 (Auto Pruning)

- 可配置的阈值（天数、失败率等）
- Dry-run 模式：只报告不执行
- 安全确认：高危操作需二次确认

## 快速开始

### 安装

```bash
git clone https://github.com/cheng2510/hermes-skill-lifecycle.git
cd hermes-skill-lifecycle
pip install -r requirements.txt
```

### 使用

```bash
# 扫描所有技能，生成健康报告
python -m src.cli scan

# 查看冲突检测结果
python -m src.cli conflicts

# 查看使用统计
python -m src.cli stats

# 生成清理建议（dry-run）
python -m src.cli prune --dry-run

# 启动 Web 仪表盘
python -m src.web_dashboard
```

### 集成到 Hermes Agent

将以下代码加入你的 Hermes Agent 配置：

```python
# 在 skill_manage 后自动触发健康检查
from src.skill_registry import SkillRegistry
registry = SkillRegistry()
registry.scan_all()
registry.generate_report()
```

## 项目结构

```
hermes-skill-lifecycle/
├── README.md                 # 本文件
├── requirements.txt          # Python 依赖
├── src/
│   ├── __init__.py
│   ├── cli.py               # CLI 入口
│   ├── skill_registry.py    # 核心注册表 + 健康评分
│   ├── conflict_detector.py # 冲突检测引擎
│   ├── usage_tracker.py     # 使用追踪 + SQLite
│   ├── auto_pruner.py       # 自动清理建议
│   └── web_dashboard.py     # Web 仪表盘（可选）
├── tests/
│   ├── __init__.py
│   ├── test_registry.py
│   ├── test_conflict.py
│   └── test_pruner.py
└── .github/
    └── workflows/
        └── ci.yml           # GitHub Actions CI
```

## 设计理念

本项目参考了以下成熟方案：

- **tech-leads-club/agent-skills** (2.3k⭐)：锁文件机制 + CI 验证
- **NousResearch/hermes-agent-self-evolution** (2.7k⭐)：进化式优化
- **rscheiwe/open-skills**：全生命周期管理
- **Dicklesworthstone/meta_skill**：多臂老虎机算法优化技能推荐
- **IBM/mcp-context-forge**：企业级注册表模式

但不是照搬，而是因地制宜：

1. **不引入外部依赖**：不强制安装 DSPy/GEPA，用纯 Python 实现
2. **兼容现有格式**：直接读取 Hermes 的 SKILL.md frontmatter
3. **渐进式采用**：可以只用扫描功能，不强制启用自动清理
4. **本地优先**：所有数据存储在本地 SQLite，不上传云端

## License

MIT
