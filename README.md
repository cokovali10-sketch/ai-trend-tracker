<div align="center">

  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f172a,50:ef4444,100:38bdf8&height=180&section=header&text=AI+Trend+Tracker&fontSize=52&fontColor=ffffff&fontAlignY=40&desc=Real-time+AI+news+aggregation+from+RSS+feeds&descSize=16&descAlignY=62&animation=fadeIn" alt="header" />

# 📡 AI Trend Tracker

### Real-time AI news aggregation and trend analysis

[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![RSS](https://img.shields.io/badge/RSS-feeds-FFA500?logo=rss&logoColor=white)](#)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## What is it?

An AI trend tracker that aggregates news from RSS feeds, analyzes trends,
and surfaces what matters in the AI space.

## Features

- 📡 RSS feed aggregation from multiple AI sources
- 🔍 Trend detection and analysis
- 📊 Dashboard for browsing trends
- ⚡ Real-time updates

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Architecture

```mermaid
flowchart LR
    RSS[RSS Feeds] --> A[Aggregator]
    A --> A2[Analyzer<br/>trend detection]
    A2 --> D[Dashboard]
```

## Honest limitations

- Depends on RSS feed availability.
- Trend analysis is keyword-based (no LLM yet).

## License

MIT

<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:38bdf8,50:ef4444,100:0f172a&height=100&section=footer" alt="footer" />
</div>
