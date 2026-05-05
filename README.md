
# 🧬 Hermes Agent Skill Lifecycle Manager
> Solving the systemic "create-but-not-maintain" problem of the Hermes Agent Skill System

## Problem Background
The Hermes Agent Skill system has the following core pain points:
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    Current Skill Ecosystem Status                  
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────|
│  ❌ Uncontrolled skill growth - No deprecation mechanism
│  ❌ No usage tracking - No visibility into which skills are actually useful
│  ❌ No conflict detection - Overlapping skills compete for triggering
│  ❌ No health assessment - Broken skills are still loaded
│  ❌ No tiered management - 89 flat-listed skills drown out core ones
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Solution Architecture
```
┌──────────────────────────────────────────────────────────────┐
│                    Skill Lifecycle Manager                      
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Registry │ Conflict │  Usage   │  Auto    │   Web Dashboard  
│  Engine  │ Detector │ Tracker  │  Pruner  │   (Optional)         
├──────────┴──────────┴──────────┴──────────┴──────────────────┤
│                    SQLite Data Layer                               
├──────────────────────────────────────────────────────────────┤
│              ~/.hermes/skills/ File System                        
└──────────────────────────────────────────────────────────────┘
```

## Core Features
### 1. Skill Health Scoring
Calculates a health score (0-100) for each skill based on multi-dimensional metrics:

| Indicator | Weight | Description |
|-----------|--------|-------------|
| Usage Frequency | 30% | Number of invocations in the last 30 days |
| Success Rate | 25% | Ratio of successful invocations to total invocations |
| Freshness | 20% | Days since the last usage |
| Dependency Level | 15% | Number of references from other skills |
| Documentation Completeness | 10% | Frontmatter field integrity and document length |

### 2. Skill Tiering
```
┌─────────────┐
│  Core Skills    │ ← Health score ≥ 80, high-frequency usage
│               
├─────────────┤
│  Candidate Skills │ ← Health score 60-79, high potential
│               
├─────────────┤
│  Watch List Skills │ ← Health score 40-59, requires attention
│               
├─────────────┤
│  Deprecated Skills  │ ← Health score < 40, recommended for cleanup
│               
└─────────────┘
```

### 3. Conflict Detection
- **Name Similarity**: Detects similar naming via Levenshtein distance
- **Description Overlap**: Detects functional duplication via TF-IDF cosine similarity
- **Tag Collision**: Detects Jaccard similarity of tag sets
- **Trigger Word Conflict**: Detects keyword overlap in the When to Use section

### 4. Usage Tracking
- SQLite storage for every skill invocation event
- Aggregated statistics: daily/weekly/monthly dimensions
- Trend analysis: identify rising/falling usage trends

### 5. Auto Pruning
- Configurable thresholds (days, failure rate, etc.)
- Dry-run mode: report only without execution
- Safety confirmation: secondary confirmation required for high-risk operations

## Quick Start
### Installation
```bash
git clone https://github.com/cheng2510/hermes-skill-lifecycle.git
cd hermes-skill-lifecycle
pip install -r requirements.txt
```

### Usage
```bash
# Scan all skills and generate a health report
python -m src.cli scan

# View conflict detection results
python -m src.cli conflicts

# View usage statistics
python -m src.cli stats

# Generate cleanup recommendations (dry-run)
python -m src.cli prune --dry-run

# Launch the web dashboard
python -m src.web_dashboard
```

### Integration with Hermes Agent
Add the following code to your Hermes Agent configuration:
```python
# Auto-trigger health check after skill_manage
from src.skill_registry import SkillRegistry
registry = SkillRegistry()
registry.scan_all()
registry.generate_report()
```

## Project Structure
```
hermes-skill-lifecycle/
├── README.md                 # This document
├── requirements.txt          # Python dependencies
├── src/
│   ├── __init__.py
│   ├── cli.py               # CLI entry point
│   ├── skill_registry.py    # Core registry + health scoring
│   ├── conflict_detector.py # Conflict detection engine
│   ├── usage_tracker.py     # Usage tracking + SQLite
│   ├── auto_pruner.py       # Auto cleanup recommendations
│   └── web_dashboard.py     # Web dashboard (Optional)
├── tests/
│   ├── __init__.py
│   ├── test_registry.py
│   ├── test_conflict.py
│   └── test_pruner.py
└── .github/
    └── workflows/
        └── ci.yml           # GitHub Actions CI
```

## Design Philosophy
This project draws inspiration from the following mature solutions:
- **tech-leads-club/agent-skills** (2.3k⭐): Lock file mechanism + CI validation
- **NousResearch/hermes-agent-self-evolution** (2.7k⭐): Evolutionary optimization
- **rscheiwe/open-skills**: Full lifecycle management
- **Dicklesworthstone/meta_skill**: Multi-armed bandit algorithm for optimized skill recommendation
- **IBM/mcp-context-forge**: Enterprise-grade registry pattern

Instead of direct replication, we tailored the solution with these core principles:
1. **No external dependencies**: No mandatory DSPy/GEPA installation, implemented in pure Python
2. **Native format compatibility**: Directly reads Hermes SKILL.md frontmatter
3. **Progressive adoption**: Can use only the scan function, no mandatory auto-pruning enablement
4. **Local-first**: All data stored in local SQLite, no cloud uploads

## License
MIT
