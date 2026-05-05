# 🧠 Hermes Agent 技能生命周期管理系统

## 项目概述

Hermes Agent 技能生命周期管理系统是一个完整的技能管理平台，解决了 Hermes Agent 当前面临的技能管理难题：89个技能缺乏使用追踪、健康评分、冲突检测和自动清理机制。本系统实现了技能从"出生到死亡"的全生命周期管理。

## 核心问题

| 问题 | 描述 | 解决方案 |
|------|------|----------|
| 无使用追踪 | 技能被加载但从未记录使用情况 | SQLite 使用事件日志 |
| 无健康评分 | 无法判断技能质量 | 多维度健康评分算法 |
| 无冲突检测 | 相似/重复技能共存 | Levenshtein + TF-IDF 检测 |
| 无自动清理 | 技能"只生不死" | 健康驱动的自动清理 |
| 无依赖管理 | 技能间关系不明确 | 依赖图构建与分析 |

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hermes 技能生命周期管理系统                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐          │
│  │ CLI 工具  │───▶│  技能注册表   │───▶│  Web 仪表板    │          │
│  └──────────┘    └──────┬───────┘    └───────────────┘          │
│                         │                                       │
│         ┌───────────────┼───────────────┐                       │
│         ▼               ▼               ▼                       │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐             │
│  │ 冲突检测器  │  │ 使用追踪器   │  │ 自动清理器    │             │
│  └─────┬──────┘  └──────┬──────┘  └──────┬───────┘             │
│        │                │                │                      │
│        ▼                ▼                ▼                      │
│  ┌─────────┐     ┌──────────┐     ┌──────────┐                 │
│  │相似度分析│     │SQLite DB │     │健康评分   │                 │
│  │标签碰撞  │     │统计聚合   │     │分级分类   │                 │
│  │触发词冲突│     │趋势分析   │     │干运行模式  │                 │
│  └─────────┘     └──────────┘     └──────────┘                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              ~/.hermes/skills/ 目录结构                    │    │
│  │  ┌──────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │    │
│  │  │ skill│  │ SKILL.md │  │ metadata │  │ usage.db │     │    │
│  │  │ dirs │  │ frontmat │  │  .json   │  │          │     │    │
│  │  └──────┘  └──────────┘  └──────────┘  └──────────┘     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## 技能分级体系

```
┌─────────────────────────────────────────────────────┐
│                   技能分级金字塔                        │
│                                                     │
│                    ┌───────┐                         │
│                    │ 核心层 │  ← 高健康分、高频使用     │
│                   ─┤       ├─                       │
│                  / └───────┘ \                       │
│                ┌──────────────┐                      │
│                │   候选层      │  ← 中等健康分          │
│               ─┤              ├─                     │
│              / └──────────────┘ \                    │
│            ┌──────────────────────┐                  │
│            │      已废弃层         │  ← 低健康分        │
│            └──────────────────────┘                  │
└─────────────────────────────────────────────────────┘
```

## 安装

```bash
# 克隆仓库
git clone https://github.com/cheng2510/hermes-skill-lifecycle.git
cd hermes-skill-lifecycle

# 安装依赖
pip install -r requirements.txt

# 安装为包
pip install -e .
```

## 使用方法

### CLI 命令

```bash
# 全面扫描技能生态系统
hermes-skills scan

# 生成健康报告
hermes-skills health

# 检测技能冲突
hermes-skills conflicts

# 获取清理建议（干运行模式）
hermes-skills prune --dry-run

# 执行清理
hermes-skills prune --execute

# 查看使用统计
hermes-skills stats
hermes-skills stats --skill <skill-name>
```

### Web 仪表板

```bash
# 启动 Web 仪表板
hermes-skills dashboard --port 5000

# 访问 http://localhost:5000
```

## 健康评分算法

每个技能的健康分数 (0-100) 由以下维度加权计算：

```
健康分 = (使用频率 × 0.30) + (成功率 × 0.25) + (新鲜度 × 0.25) + (依赖质量 × 0.20)
```

| 维度 | 权重 | 计算方式 |
|------|------|----------|
| 使用频率 | 30% | 近30天使用次数归一化 |
| 成功率 | 25% | 成功执行次数/总执行次数 |
| 新鲜度 | 25% | 最后使用时间衰减函数 |
| 依赖质量 | 20% | 依赖数量和健康度 |

## 冲突检测

系统通过四种方式检测技能间冲突：

1. **名称相似度** - Levenshtein 编辑距离，阈值 0.8
2. **描述重叠** - TF-IDF 向量化 + 余弦相似度，阈值 0.7
3. **标签碰撞** - 集合交集检测
4. **触发词冲突** - 相同关键词触发不同技能

## 目录结构

```
hermes-skill-lifecycle/
├── README.md                    # 本文件
├── requirements.txt             # Python 依赖
├── setup.py                     # 包安装配置
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI
├── src/
│   ├── __init__.py
│   ├── skill_registry.py       # 核心注册表
│   ├── conflict_detector.py    # 冲突检测器
│   ├── usage_tracker.py        # 使用追踪器
│   ├── auto_pruner.py          # 自动清理器
│   ├── cli.py                  # CLI 接口
│   └── web_dashboard.py        # Web 仪表板
└── tests/
    ├── __init__.py
    ├── test_registry.py
    ├── test_conflict.py
    ├── test_tracker.py
    └── test_pruner.py
```

## 开发

```bash
# 运行测试
pytest tests/ -v

# 运行带覆盖率的测试
pytest tests/ -v --cov=src --cov-report=html

# 代码风格检查
flake8 src/ tests/
black --check src/ tests/
```

## 许可证

MIT License

## 致谢

- [tech-leads-club/agent-skills](https://github.com/tech-leads-club/agent-skills) - 锁文件注册表模式
- [NousResearch/hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) - 进化优化
- [rscheiwe/open-skills](https://github.com/rscheiwe/open-skills) - 生命周期管理
- [Dicklesworthstone/meta_skill](https://github.com/Dicklesworthstone/meta_skill) - 多臂老虎机建议
- [IBM/mcp-context-forge](https://github.com/IBM/mcp-context-forge) - 企业级网关注册
