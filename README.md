# 🧬 Hermes Agent Skill Lifecycle Manager

> 解决 Hermes Agent 技能系统"只生不养"的系统性问题

## 问题背景

Hermes Agent 的 Skill 系统存在以下核心问题：

| 问题 | 说明 |
|------|------|
| ❌ 技能只增不减 | 没有淘汰机制，技能数只增不减 |
| ❌ 无使用追踪 | 不知道哪些技能有用、哪些是死代码 |
| ❌ 无冲突检测 | 功能重叠的技能互相争抢 context |
| ❌ 无健康评估 | 坏掉的技能照样被加载，浪费 token |
| ❌ 无分层管理 | 89+ 技能平铺，核心技能被淹没 |

## 解决方案

```
┌──────────────────────────────────────────────────────────────┐
│                    Skill Lifecycle Manager                      │
├──────────┬──────────┬──────────┬──────────┬──────────────────
│ Registry │ Conflict │  Usage   │  Auto    │   CLI / Web      
│  Engine  │ Detector │ Tracker  │  Pruner  │   Dashboard      
├──────────┴──────────┴──────────┴──────────┴──────────────────
│                    SQLite 数据层                               │
├──────────────────────────────────────────────────────────────
│              ~/.hermes/skills/ 文件系统                        │
└──────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 技能健康度评分 (Skill Health Scoring)

多维度指标计算每个技能的健康分（0-100）：

| 指标 | 权重 | 说明 |
|------|------|------|
| 使用频率 | 30% | 最近 30 天被调用的次数 |
| 成功率 | 25% | 调用成功/总调用比 |
| 新鲜度 | 20% | 最后一次使用距今天数 |
| 依赖度 | 15% | 被其他技能引用的次数 |
| 文档完整度 | 10% | frontmatter 字段完整性和文档长度 |

**智能基线**：无追踪数据时给中性分（不会把新技能全标红），有追踪但无记录时轻微惩罚。

### 2. 技能分层 (Skill Tiering)

| 层级 | 分数范围 | 含义 |
|------|----------|------|
| 🟢 核心 (Core) | ≥ 80 | 高频使用，文档完善 |
| 🔵 候选 (Candidate) | 60-79 | 有潜力，值得保留 |
| 🟡 观察 (Watch) | 40-59 | 需要关注，可能需要改进文档 |
| 🔴 待淘汰 (Deprecated) | < 40 | 建议清理 |

### 3. 冲突检测 (Conflict Detection)

- **名称相似度**：Levenshtein 编辑距离（真正的编辑距离，不是字符集交集）
- **描述重叠度**：词频向量 Jaccard 相似度
- **标签碰撞**：Jaccard 相似度
- **触发词冲突**：关键词重叠检测（过滤停用词）

### 4. 使用追踪 (Usage Tracking)

- SQLite 存储每次技能调用事件
- 统计聚合：日/周/月维度
- 通过 CLI 的 `record` 命令记录使用

### 5. 自动清理 (Auto Pruning)

- 基于健康度评分和使用数据生成清理建议
- Dry-run 模式（默认）：只报告不执行
- 无使用数据时不盲目建议删除

## 快速开始

### 安装

```bash
git clone https://github.com/cheng2510/hermes-skill-lifecycle.git
cd hermes-skill-lifecycle
pip install -e .
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
python -m src.cli prune

# 记录一次技能使用
python -m src.cli record my-skill
python -m src.cli record my-skill --failed

# 全部报告
python -m src.cli all
```

### Web 仪表盘（可选）

```bash
pip install flask
python -m src.web_dashboard
# 访问 http://localhost:5555
```

## 项目结构

```
hermes-skill-lifecycle/
├── README.md
├── requirements.txt
├── setup.py
├── src/
│   ├── __init__.py
│   ├── cli.py               # CLI 入口
│   ├── skill_registry.py    # 核心注册表 + 健康评分
│   ├── conflict_detector.py # 冲突检测引擎
│   ├── usage_tracker.py     # 使用追踪 + SQLite
│   ├── auto_pruner.py       # 自动清理建议
│   └── web_dashboard.py     # Web 仪表盘
└── tests/
    ├── test_registry.py
    ├── test_conflict.py
    ├── test_pruner.py
    └── test_tracker.py
```

## 设计理念

1. **不引入外部依赖**：核心只依赖 pyyaml，纯 Python 实现
2. **兼容现有格式**：直接读取 Hermes 的 SKILL.md frontmatter
3. **渐进式采用**：可以只用扫描功能，不强制启用自动清理
4. **本地优先**：所有数据存储在本地 SQLite，不上传云端
5. **智能评分**：区分"无追踪系统"、"有系统无记录"、"有实际数据"三种状态

## License

MIT
