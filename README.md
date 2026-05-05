<div align="right">

[**简体中文**](README_zh_CN.md)

</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white" alt="Python 3.9+"/>
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"/>
  <img src="https://img.shields.io/badge/Tests-15/15-brightgreen.svg" alt="Tests 15/15"/>
  <img src="https://img.shields.io/badge/Version-1.1.0-orange.svg" alt="Version 1.1.0"/>
</p>

<h1 align="center">🧬 Skill Lifecycle Manager</h1>
<p align="center"><b>Stop hoarding dead skills. Start managing them.</b></p>
<p align="center">A health scoring, conflict detection, and usage tracking system for <a href="https://github.com/NousResearch/hermes-agent">Hermes Agent</a> skills.</p>

---

## The Problem

Hermes Agent loads **every** skill into context on every turn. With 80+ skills, that's a lot of tokens burned on skills nobody ever uses. Worse, there's no way to know:

- Which skills are actually useful vs. dead weight
- Which skills overlap and compete for the same triggers
- Which skills are broken and should be removed
- Which skills matter most and deserve priority

**The skill system only grows. It never prunes.**

## The Solution

```
┌─────────────────────────────────────────────────────────────────┐
│                   Skill Lifecycle Manager                         
├────────────┬────────────┬────────────┬────────────┬─────────────┤
│  Health    │  Conflict  │   Usage    │   Auto     │    CLI &    │
│  Scoring   │  Detector  │   Tracker  │   Pruner   │   Dashboard │
├────────────┴────────────┴────────────┴────────────┴─────────────┤
│                      SQLite Storage Layer                         
├─────────────────────────────────────────────────────────────────┤
│                 ~/.hermes/skills/ (SKILL.md files)                
└─────────────────────────────────────────────────────────────────┘
```

## Features

### Health Scoring (0-100)

Every skill gets a composite health score based on five weighted dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Usage Frequency | 30% | Calls in the last 30 days |
| Success Rate | 25% | Successful calls / total calls |
| Freshness | 20% | Days since last use |
| Dependency | 15% | How many other skills reference it |
| Documentation | 10% | Frontmatter completeness + doc length |

**Smart baselines** — three tiers of data awareness:
- No tracking system installed → neutral score (50)
- Tracking installed but skill has no records → mild penalty (30)
- Skill has real usage data → actual scoring

### Skill Tiering

```
  ┌─────────────────────────────────────────────┐
  │  🟢 Core        │  score ≥ 80  │  Keep      
  │  🔵 Candidate   │  60 – 79     │  Promising  
  │  🟡 Watch       │  40 – 59     │  Monitor    
  │  🔴 Deprecated  │  < 40        │  Prune      
  └─────────────────────────────────────────────┘
```

### Conflict Detection

Four independent detection engines run in parallel:

| Engine | Method | Catches |
|--------|--------|---------|
| Name Similarity | Levenshtein edit distance | `github-pr` vs `github-pr-workflow` |
| Description Overlap | Token-level Jaccard | Two skills that do the same thing |
| Tag Collision | Set Jaccard | `["git","pr"]` vs `["git","review"]` |
| Trigger Word Overlap | Keyword intersection (stopwords filtered) | Competing trigger phrases |

### Usage Tracking

```bash
# Record a skill use
python -m src.cli record my-skill

# Record a failure
python -m src.cli record my-skill --failed

# View statistics
python -m src.cli stats --days 7
```

All data lives in `~/.hermes/skill_lifecycle.db` (SQLite). Nothing leaves your machine.

### Auto Pruning

Generates cleanup suggestions without touching your files. Three action types:

| Action | Meaning |
|--------|---------|
| 📉 Deprecate | Mark as low-priority |
| 🗑️ Remove | Safe to delete |
| 🔗 Merge | Two skills should become one |

Dry-run by default. No data? No blind deletions.

## Quick Start

### Install

```bash
git clone https://github.com/cheng2510/hermes-skill-lifecycle.git
cd hermes-skill-lifecycle
pip install -e .
```

### CLI Usage

```bash
# Full health report
python -m src.cli scan

# Conflict detection
python -m src.cli conflicts

# Usage statistics (last 30 days)
python -m src.cli stats

# Cleanup suggestions (dry-run)
python -m src.cli prune

# Everything at once
python -m src.cli all
```

### Example Output

```
============================================================
  Hermes Agent Skill Ecosystem Health Report
============================================================
  Scan time: 2026-05-05 17:38:11
  Total skills: 92

  ┌─────────────┬───────┐
  │ Tier        │ Count │
  ├─────────────┼───────┤
  │ 🟢 Core         │ 0 │
  │ 🔵 Candidate    │ 1 │
  │ 🟡 Watch        │91 │
  │ 🔴 Deprecated   │ 0 │
  └─────────────┴───────┘

  Skill Health Ranking:
  --------------------------------------------------------
   1. [🔵 Candidate]  60.0 |████████████░░░░░░░░| test-driven-development
   2. [🟡 Watch    ]  58.8 |███████████░░░░░░░░░| claude-design
   3. [🟡 Watch    ]  58.0 |███████████░░░░░░░░░| excalidraw
   4. [🟡 Watch    ]  58.0 |███████████░░░░░░░░░| writing-plans
   ...
```

### Web Dashboard (Optional)

```bash
pip install flask
python -m src.web_dashboard
# → http://localhost:5555
```

Dark-themed dashboard with real-time health cards, tier breakdowns, and conflict visualization.

## Project Structure

```
hermes-skill-lifecycle/
├── src/
│   ├── cli.py               # CLI entry point
│   ├── skill_registry.py    # Scanner + health scoring engine
│   ├── conflict_detector.py # 4-dimension conflict detection
│   ├── usage_tracker.py     # SQLite usage event tracker
│   ├── auto_pruner.py       # Cleanup suggestion generator
│   └── web_dashboard.py     # Flask web dashboard
├── tests/
│   ├── test_registry.py
│   ├── test_conflict.py
│   ├── test_pruner.py
│   └── test_tracker.py
├── setup.py
├── requirements.txt
└── README.md
```

## Design Principles

1. **Zero heavy dependencies** — core runs on `pyyaml` alone. No sklearn, no numpy, no jieba.
2. **Reads native format** — parses Hermes `SKILL.md` frontmatter directly. No migration needed.
3. **Adopt incrementally** — use `scan` alone. Never forced to enable auto-pruning.
4. **Local-first** — all data in local SQLite. Nothing uploaded. Nothing phones home.
5. **Smart baselines** — distinguishes "no tracker" / "tracker exists but no data" / "real data" so fresh installs don't panic.

## Running Tests

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

## Contributing

Issues and PRs welcome. This project is actively maintained — every optimization gets synced to this repo automatically.

## License

[MIT](LICENSE)
