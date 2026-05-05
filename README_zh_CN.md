<div align="right">

[**English**](README.md)

</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white" alt="Python 3.9+"/>
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"/>
  <img src="https://img.shields.io/badge/Tests-15/15-brightgreen.svg" alt="Tests 15/15"/>
  <img src="https://img.shields.io/badge/Version-1.1.0-orange.svg" alt="Version 1.1.0"/>
</p>

<h1 align="center">🧬 Skill Lifecycle Manager</h1>
<p align="center"><b>别再囤积没用的技能了，管管它们吧。</b></p>
<p align="center"><a href="https://github.com/NousResearch/hermes-agent">Hermes Agent</a> 技能健康评分、冲突检测与使用追踪系统。</p>

---

## 问题是什么

Hermes Agent 每次对话都会把**所有**技能加载到 context 里。80+ 个技能，大量 token 浪费在没人用的技能上。更糟的是，你根本不知道：

- 哪些技能真正有用，哪些是 dead weight
- 哪些技能功能重叠，互相争抢触发词
- 哪些技能已经坏掉，应该删掉
- 哪些技能最重要，值得优先保留

**技能系统只增不减，从不清理。**

## 解决方案

```
┌─────────────────────────────────────────────────────────────────┐
│                   Skill Lifecycle Manager                          
├────────────┬────────────┬────────────┬────────────┬─────────────┤
│  健康评分   │  冲突检测   │  使用追踪   │  自动清理   │  CLI 仪表盘  
├────────────┴────────────┴────────────┴────────────┴─────────────┤
│                      SQLite 存储层                                
├─────────────────────────────────────────────────────────────────┤
│              ~/.hermes/skills/ (SKILL.md 文件)                    
└─────────────────────────────────────────────────────────────────┘
```

## 功能特性

### 健康评分 (0-100)

每个技能根据五个加权维度计算综合健康分：

| 维度 | 权重 | 说明 |
|------|------|------|
| 使用频率 | 30% | 最近 30 天的调用次数 |
| 成功率 | 25% | 成功调用 / 总调用 |
| 新鲜度 | 20% | 距离上次使用的天数 |
| 依赖度 | 15% | 被其他技能引用的次数 |
| 文档完整度 | 10% | frontmatter 完整性 + 文档长度 |

**智能基线** — 三级数据感知：
- 没有追踪系统 → 中性分 (50)
- 有追踪但该技能无记录 → 轻微惩罚 (30)
- 有实际使用数据 → 真实评分

### 技能分层

```
  ┌─────────────────────────────────────────────┐
  │  🟢 核心 (Core)      │  分数 ≥ 80  │  保留    
  │  🔵 候选 (Candidate) │  60 – 79    │  有潜力 
  │  🟡 观察 (Watch)     │  40 – 59    │  关注   
  │  🔴 待淘汰 (Deprecated) │ < 40     │  清理    
  └─────────────────────────────────────────────┘
```

### 冲突检测

四个独立检测引擎并行运行：

| 引擎 | 方法 | 检测目标 |
|------|------|----------|
| 名称相似度 | Levenshtein 编辑距离 | `github-pr` vs `github-pr-workflow` |
| 描述重叠 | Token 级 Jaccard 相似度 | 两个做同一件事的技能 |
| 标签碰撞 | 集合 Jaccard | `["git","pr"]` vs `["git","review"]` |
| 触发词重叠 | 关键词交集（过滤停用词） | 竞争触发词 |

### 使用追踪

```bash
# 记录一次技能使用
python -m src.cli record my-skill

# 记录失败
python -m src.cli record my-skill --failed

# 查看统计
python -m src.cli stats --days 7
```

所有数据存储在 `~/.hermes/skill_lifecycle.db` (SQLite)。数据不出本机。

### 自动清理

基于健康评分和使用数据生成清理建议，不直接改文件。三种动作：

| 动作 | 含义 |
|------|------|
| 📉 淘汰 | 标记为低优先级 |
| 🗑️ 移除 | 可以安全删除 |
| 🔗 合并 | 两个技能应该合为一个 |

默认 dry-run 模式。没有使用数据时不会盲目建议删除。

## 快速开始

### 安装

```bash
git clone https://github.com/cheng2510/hermes-skill-lifecycle.git
cd hermes-skill-lifecycle
pip install -e .
```

### CLI 使用

```bash
# 完整健康报告
python -m src.cli scan

# 冲突检测
python -m src.cli conflicts

# 使用统计（最近 30 天）
python -m src.cli stats

# 清理建议（dry-run）
python -m src.cli prune

# 全部报告
python -m src.cli all
```

### 输出示例

```
============================================================
  Hermes Agent 技能生态健康报告
============================================================
  扫描时间: 2026-05-05 17:38:11
  技能总数: 92

  ┌─────────────┬───────┐
  │ 层级         │ 数量 
  ├─────────────┼───────┤
  │ 🟢 核心技能        0 
  │ 🔵 候选技能        1 
  │ 🟡 观察技能       91 
  │ 🔴 待淘汰技能      0 
  └─────────────┴───────┘

  技能健康度排行:
  --------------------------------------------------------
   1. [🔵 候选技能]  60.0 |████████████░░░░░░░░| test-driven-development
   2. [🟡 观察技能]  58.8 |███████████░░░░░░░░░| claude-design
   3. [🟡 观察技能]  58.0 |███████████░░░░░░░░░| excalidraw
   4. [🟡 观察技能]  58.0 |███████████░░░░░░░░░| writing-plans
   ...
```

### Web 仪表盘（可选）

```bash
pip install flask
python -m src.web_dashboard
# → http://localhost:5555
```

深色主题仪表盘，实时健康卡片、分层概览和冲突可视化。

## 项目结构

```
hermes-skill-lifecycle/
├── src/
│   ├── cli.py               # CLI 入口
│   ├── skill_registry.py    # 扫描器 + 健康评分引擎
│   ├── conflict_detector.py # 四维冲突检测
│   ├── usage_tracker.py     # SQLite 使用事件追踪
│   ├── auto_pruner.py       # 清理建议生成器
│   └── web_dashboard.py     # Flask Web 仪表盘
├── tests/
│   ├── test_registry.py
│   ├── test_conflict.py
│   ├── test_pruner.py
│   └── test_tracker.py
├── setup.py
├── requirements.txt
└── README.md
```

## 设计原则

1. **零重依赖** — 核心仅依赖 `pyyaml`，不需要 sklearn、numpy、jieba
2. **读原生格式** — 直接解析 Hermes `SKILL.md` frontmatter，无需迁移
3. **渐进式采用** — 只用 `scan` 也可以，不强制开启自动清理
4. **本地优先** — 所有数据存本地 SQLite，不上传云端
5. **智能基线** — 区分"无追踪系统" / "有系统无记录" / "有实际数据"，新装不会全报红

## 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

```
tests/test_registry.py  ✓  5/5
tests/test_conflict.py  ✓  4/4
tests/test_pruner.py    ✓  2/2
tests/test_tracker.py   ✓  4/4
─────────────────────────────
                        15 passed
```

## 贡献

欢迎 Issue 和 PR。项目持续维护中 — 每次优化都会同步更新到仓库。

## 许可证

[MIT](LICENSE)
