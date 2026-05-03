#!/usr/bin/env python3
"""
SPEECH COACH - Progress Dashboard Generator
RUN: python3 ~/SpeechCoach/progress.py
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime

DATA_FILE = Path.home() / "SpeechCoach/progress_data.json"
DASHBOARD_FILE = Path.home() / "SpeechCoach/dashboard.html"

CONTEXT_COLORS = {
    "thinking": "#7c6aff",
    "pitch": "#ff6a9e",
    "mentor": "#6affd4",
    "rubber_ducking": "#ffd24d",
    "brainstorm": "#ff9f6a",
    "feedback": "#6ab8ff",
    "learning": "#b86aff",
    "decision": "#6affb8"
}

CONTEXT_EMOJI = {
    "thinking": "💭",
    "pitch": "🚀",
    "mentor": "🎓",
    "rubber_ducking": "🦆",
    "brainstorm": "⚡",
    "feedback": "📋",
    "learning": "📚",
    "decision": "⚖️"
}

def load_data():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def clean_sessions(sessions):
    """Fix zero scores and remove truly empty sessions."""
    cleaned = []
    for s in sessions:
        # Skip sessions with no words at all
        if s.get("total_words", 0) == 0:
            continue
        # Fix zero scores — if 0, they failed to parse, use baseline
        if s.get("clarity_score", 0) == 0:
            s["clarity_score"] = 6  # baseline
        if s.get("confidence_score", 0) == 0:
            s["confidence_score"] = 7  # baseline
        # Fix missing context
        if not s.get("context") or s.get("context") == "unknown":
            s["context"] = "thinking"
            s["context_label"] = "Thinking Out Loud"
        # Flag short sessions
        words = s.get("total_words", 0)
        if words < 50:
            continue  # skip entirely
        elif words < 100:
            s["short_session"] = True
        else:
            s["short_session"] = False

        cleaned.append(s)
    return cleaned

def truncate(text, max_chars=80):
    """Truncate pattern text to a short punchy label."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + "..."

def generate_dashboard(sessions: list):
    if not sessions:
        print("No session data yet. Complete a session first.")
        return

    sessions = clean_sessions(sessions)
    if not sessions:
        print("No valid sessions found after cleaning.")
        return

    dates = [s.get("date", "") for s in sessions]
    filler_rates = [s.get("filler_rate", 0) for s in sessions]
    clarity_scores = [s.get("clarity_score", 0) for s in sessions]
    confidence_scores = [s.get("confidence_score", 0) for s in sessions]
    contexts = [s.get("context", "thinking") for s in sessions]

    latest = sessions[-1]
    first = sessions[0]
    filler_change = round(latest.get("filler_rate", 0) - first.get("filler_rate", 0), 1)
    clarity_change = latest.get("clarity_score", 0) - first.get("clarity_score", 0)
    confidence_change = latest.get("confidence_score", 0) - first.get("confidence_score", 0)

    # Overall trend
    improving = (filler_change <= 0 and clarity_change >= 0) or clarity_change > 0
    trend_label = "Trending Up 📈" if improving else "Needs Work 📉"
    trend_color = "#4dffb4" if improving else "#ff4d6a"

    # Rewrites — find most recent session that actually has rewrites
    best_rewrite_session = next(
        (s for s in reversed(sessions) if s.get("rewrites")),
        latest
    )
    latest_rewrites = best_rewrite_session.get("rewrites", [])
    todays_focus = best_rewrite_session.get("todays_focus", "")

    rewrites_html = ""
    if latest_rewrites:
        for i, r in enumerate(latest_rewrites):
            rewrites_html += f"""
        <div class="rewrite-block">
            <div class="rewrite-num">#{i+1}</div>
            <div class="rewrite-content">
                <div class="rewrite-said">
                    <span class="rewrite-label bad">Said</span>
                    <span class="rewrite-text">"{r.get('said','')}"</span>
                </div>
                <div class="rewrite-arrow">↓</div>
                <div class="rewrite-better">
                    <span class="rewrite-label good">Better</span>
                    <span class="rewrite-text">"{r.get('better','')}"</span>
                </div>
                <div class="rewrite-why">💡 {r.get('why','')}</div>
            </div>
        </div>"""
    else:
        rewrites_html = '<p class="empty-msg">Complete a session to see rewrite suggestions.</p>'

    focus_html = f"""
    <div class="focus-box">
        <div class="focus-label">TODAY'S FOCUS</div>
        <div class="focus-text">{todays_focus if todays_focus else "Complete a session to get your daily focus."}</div>
    </div>""" if todays_focus else ""

    # Context breakdown
    context_counts = {}
    for s in sessions:
        c = s.get("context", "thinking")
        if c and c != "unknown":
            label = s.get("context_label", c.title())
            if label not in context_counts:
                context_counts[label] = {"count": 0, "key": c}
            context_counts[label]["count"] += 1

    # Top patterns — short only
    pattern_counts = {}
    for s in sessions:
        for p in s.get("patterns", []):
            short = truncate(p, 70)
            pattern_counts[short] = pattern_counts.get(short, 0) + 1
    top_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Session rows
    session_rows = ""
    for s in reversed(sessions[-10:]):
        ctx = s.get("context", "thinking")
        color = CONTEXT_COLORS.get(ctx, "#7c6aff")
        emoji = CONTEXT_EMOJI.get(ctx, "💭")
        label = s.get("context_label", ctx.title())
        fr = s.get("filler_rate", 0)
        filler_color = "#ff4d6a" if fr > 5 else "#ffd24d" if fr > 3 else "#4dffb4"
        cl = s.get("clarity_score", 0)
        co = s.get("confidence_score", 0)
        cl_color = "#4dffb4" if cl >= 7 else "#ffd24d" if cl >= 5 else "#ff4d6a"
        co_color = "#4dffb4" if co >= 7 else "#ffd24d" if co >= 5 else "#ff4d6a"
        is_short = s.get("short_session", False)
        short_badge = ' <span style="font-size:9px;color:#555;background:#1a1a1a;padding:1px 6px;border-radius:4px;border:1px solid #333;font-family:IBM Plex Mono,monospace">short</span>' if is_short else ""
        scores_note = '<span style="color:#444;font-size:10px"> *</span>' if is_short else ""
        session_rows += f"""
        <tr>
            <td class="mono">{s.get("date","")}&nbsp;{s.get("time","")}{short_badge}</td>
            <td><span class="badge" style="color:{color};border-color:{color}">{emoji} {label}</span></td>
            <td class="mono center">{s.get("total_words",0)}</td>
            <td class="mono center" style="color:{filler_color};font-weight:600">{fr}</td>
            <td class="mono center" style="color:{cl_color}">{cl}/10{scores_note}</td>
            <td class="mono center" style="color:{co_color}">{co}/10{scores_note}</td>
        </tr>"""

    # Context pills
    context_pills = ""
    for label, data in sorted(context_counts.items(), key=lambda x: x[1]["count"], reverse=True):
        color = CONTEXT_COLORS.get(data["key"], "#7c6aff")
        emoji = CONTEXT_EMOJI.get(data["key"], "💭")
        context_pills += f"""
        <div class="ctx-pill">
            <span>{emoji} {label}</span>
            <span class="ctx-count" style="color:{color}">{data["count"]}</span>
        </div>"""

    # Patterns
    patterns_html = ""
    for pattern, count in top_patterns:
        patterns_html += f"""
        <div class="pattern-row">
            <span class="pattern-dot"></span>
            <span class="pattern-text">{pattern}</span>
            <span class="pattern-badge">{count}x</span>
        </div>"""

    if not patterns_html:
        patterns_html = '<p class="empty-msg">Complete more sessions to see patterns.</p>'

    # Insights
    best = max(sessions, key=lambda x: x.get("clarity_score", 0))
    most_fillers = max(sessions, key=lambda x: x.get("filler_rate", 0))
    total_mins = sum(s.get("duration_minutes", 0) for s in sessions)
    total_words_all = sum(s.get("total_words", 0) for s in sessions)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Speech Coach</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}

:root {{
  --bg: #0c0c0c;
  --s1: #111111;
  --s2: #161616;
  --border: #222222;
  --border2: #2a2a2a;
  --text: #e8e8e8;
  --muted: #555555;
  --muted2: #3a3a3a;
  --green: #4dffb4;
  --red: #ff4d6a;
  --yellow: #ffd24d;
  --blue: #4d9fff;
  --accent: #ffffff;
}}

body {{
  background: var(--bg);
  color: var(--text);
  font-family: 'IBM Plex Sans', sans-serif;
  padding: 32px 40px;
  max-width: 1300px;
  margin: 0 auto;
  font-size: 14px;
}}

.mono {{ font-family: 'IBM Plex Mono', monospace; }}

/* HEADER */
.header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border);
}}

.header-left {{
  display: flex;
  align-items: center;
  gap: 16px;
}}

.header-icon {{
  width: 40px; height: 40px;
  background: var(--s2);
  border: 1px solid var(--border2);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
}}

.header-title {{
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.3px;
}}

.header-sub {{
  font-size: 11px;
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
  margin-top: 2px;
}}

.header-stats {{
  display: flex;
  gap: 8px;
}}

.stat-tag {{
  background: var(--s2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 12px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: var(--muted);
}}

.stat-tag b {{ color: var(--text); }}

/* TREND BANNER */
.trend-banner {{
  background: var(--s1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 20px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}}

.trend-left {{
  display: flex;
  align-items: center;
  gap: 20px;
}}

.trend-status {{
  font-size: 13px;
  font-weight: 600;
  color: {trend_color};
}}

.trend-divider {{
  width: 1px; height: 20px;
  background: var(--border2);
}}

.trend-detail {{
  font-size: 12px;
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
}}

.trend-right {{
  font-size: 11px;
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
}}

/* METRICS */
.metrics {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}}

.metric {{
  background: var(--s1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px 24px;
}}

.metric-label {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
  margin-bottom: 12px;
}}

.metric-row {{
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}}

.metric-val {{
  font-size: 40px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
  line-height: 1;
}}

.metric-unit {{
  font-size: 13px;
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
}}

.metric-delta {{
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
  margin-bottom: 4px;
}}

.metric-base {{
  font-size: 10px;
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
}}

.up {{ color: var(--green); }}
.down {{ color: var(--red); }}
.flat {{ color: var(--muted); }}

/* PROGRESS BAR */
.progress-bar-wrap {{
  margin-top: 10px;
}}

.progress-bar-bg {{
  background: var(--s2);
  border-radius: 4px;
  height: 4px;
  overflow: hidden;
  margin-top: 4px;
}}

.progress-bar-fill {{
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}}

/* MAIN GRID */
.main-grid {{
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  margin-bottom: 24px;
}}

.card {{
  background: var(--s1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px 24px;
}}

.card-title {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
  margin-bottom: 20px;
}}

.chart-wrap {{
  position: relative;
  height: 200px;
}}

/* CONTEXT PILLS */
.ctx-pills {{ display: flex; flex-direction: column; gap: 8px; }}

.ctx-pill {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--s2);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
}}

.ctx-count {{
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  font-size: 14px;
}}

/* BOTTOM GRID */
.bottom-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 24px;
}}

/* PATTERNS */
.pattern-row {{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}}

.pattern-row:last-child {{ border-bottom: none; }}

.pattern-dot {{
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--muted2);
  margin-top: 5px;
  flex-shrink: 0;
}}

.pattern-text {{
  font-size: 13px;
  color: var(--text);
  flex: 1;
  line-height: 1.5;
}}

.pattern-badge {{
  font-size: 10px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--muted);
  background: var(--s2);
  padding: 2px 8px;
  border-radius: 20px;
  white-space: nowrap;
  margin-top: 2px;
}}

/* INSIGHTS */
.insight-row {{
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}}

.insight-row:last-child {{ border-bottom: none; }}

.insight-label {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
  margin-bottom: 4px;
}}

.insight-val {{
  font-size: 13px;
  color: var(--text);
  font-family: 'IBM Plex Mono', monospace;
}}

/* TABLE */
.table-card {{
  background: var(--s1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 24px;
  overflow-x: auto;
}}

table {{ width: 100%; border-collapse: collapse; }}

th {{
  text-align: left;
  padding: 6px 12px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}}

th.center, td.center {{ text-align: center; }}

td {{
  padding: 12px 12px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
}}

tr:last-child td {{ border-bottom: none; }}
tr:hover td {{ background: rgba(255,255,255,0.02); }}

.badge {{
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  border: 1px solid;
  white-space: nowrap;
  background: rgba(255,255,255,0.03);
}}

.empty-msg {{
  font-size: 12px;
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
  padding: 8px 0;
}}

/* FOOTER */
.footer {{
  text-align: center;
  color: var(--muted);
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}}

/* REWRITES */
.focus-box {{
  background: var(--s2);
  border: 1px solid var(--border2);
  border-left: 3px solid var(--yellow);
  border-radius: 8px;
  padding: 14px 18px;
  margin-bottom: 20px;
}}

.focus-label {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--yellow);
  font-family: 'IBM Plex Mono', monospace;
  margin-bottom: 6px;
}}

.focus-text {{
  font-size: 14px;
  color: var(--text);
  line-height: 1.5;
  font-weight: 500;
}}

.rewrite-block {{
  display: flex;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid var(--border);
}}

.rewrite-block:last-child {{ border-bottom: none; }}

.rewrite-num {{
  font-size: 11px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--muted);
  padding-top: 2px;
  min-width: 20px;
}}

.rewrite-content {{ flex: 1; }}

.rewrite-said, .rewrite-better {{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 4px;
}}

.rewrite-label {{
  font-size: 10px;
  font-family: 'IBM Plex Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  margin-top: 1px;
}}

.rewrite-label.bad {{
  background: rgba(255,77,106,0.15);
  color: var(--red);
}}

.rewrite-label.good {{
  background: rgba(77,255,180,0.15);
  color: var(--green);
}}

.rewrite-text {{
  font-size: 13px;
  color: var(--text);
  line-height: 1.5;
}}

.rewrite-arrow {{
  font-size: 14px;
  color: var(--muted);
  margin: 4px 0 4px 30px;
}}

.rewrite-why {{
  font-size: 12px;
  color: var(--muted);
  margin-top: 8px;
  font-style: italic;
  line-height: 1.5;
}}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div class="header-left">
    <div class="header-icon">🎙️</div>
    <div>
      <div class="header-title">Speech Coach</div>
      <div class="header-sub">generated {datetime.now().strftime('%b %d, %Y · %I:%M %p')}</div>
    </div>
  </div>
  <div class="header-stats">
    <div class="stat-tag"><b>{len(sessions)}</b> sessions</div>
    <div class="stat-tag"><b>{total_words_all}</b> words</div>
    <div class="stat-tag"><b>{total_mins}</b> min practice</div>
  </div>
</div>

<!-- TREND BANNER -->
<div class="trend-banner">
  <div class="trend-left">
    <div class="trend-status">{trend_label}</div>
    <div class="trend-divider"></div>
    <div class="trend-detail">
      Fillers {'↓' if filler_change < 0 else '↑' if filler_change > 0 else '→'} {abs(filler_change)}/100w &nbsp;·&nbsp;
      Clarity {'↑' if clarity_change > 0 else '↓' if clarity_change < 0 else '→'} {abs(clarity_change)} &nbsp;·&nbsp;
      Confidence {'↑' if confidence_change > 0 else '↓' if confidence_change < 0 else '→'} {abs(confidence_change)}
      &nbsp;since first session
    </div>
  </div>
  <div class="trend-right">Baseline: 7.1 fillers · 6/10 clarity · 7/10 confidence &nbsp;|&nbsp; Goal: &lt;3 · 8/10 · 9/10</div>
</div>

<!-- METRICS -->
<div class="metrics">
  <!-- FILLER -->
  <div class="metric">
    <div class="metric-label">Filler Rate</div>
    <div class="metric-row">
      <div class="metric-val" style="color:{'var(--red)' if latest.get('filler_rate',0) > 5 else 'var(--yellow)' if latest.get('filler_rate',0) > 3 else 'var(--green)'}">{latest.get("filler_rate",0)}</div>
      <div class="metric-unit">per 100 words</div>
    </div>
    <div class="metric-delta {'down' if filler_change > 0 else 'up' if filler_change < 0 else 'flat'}">
      {'↑ worse by ' if filler_change > 0 else '↓ better by ' if filler_change < 0 else '→ no change'}{abs(filler_change) if filler_change != 0 else ''} since start
    </div>
    <div class="metric-base">baseline 7.1 · goal &lt;3</div>
    <div class="progress-bar-wrap">
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" style="width:{min(100, (7.1 - latest.get('filler_rate',0)) / 7.1 * 100):.0f}%;background:var(--green)"></div>
      </div>
    </div>
  </div>

  <!-- CLARITY -->
  <div class="metric">
    <div class="metric-label">Thinking Clarity</div>
    <div class="metric-row">
      <div class="metric-val" style="color:{'var(--green)' if latest.get('clarity_score',0) >= 7 else 'var(--yellow)' if latest.get('clarity_score',0) >= 5 else 'var(--red)'}">{latest.get("clarity_score",0)}</div>
      <div class="metric-unit">/ 10</div>
    </div>
    <div class="metric-delta {'up' if clarity_change > 0 else 'down' if clarity_change < 0 else 'flat'}">
      {'↑ improved by ' if clarity_change > 0 else '↓ dropped by ' if clarity_change < 0 else '→ no change'}{abs(clarity_change) if clarity_change != 0 else ''} since start
    </div>
    <div class="metric-base">baseline 6 · goal 8</div>
    <div class="progress-bar-wrap">
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" style="width:{latest.get('clarity_score',0) / 8 * 100:.0f}%;background:var(--blue)"></div>
      </div>
    </div>
  </div>

  <!-- CONFIDENCE -->
  <div class="metric">
    <div class="metric-label">Confidence</div>
    <div class="metric-row">
      <div class="metric-val" style="color:{'var(--green)' if latest.get('confidence_score',0) >= 7 else 'var(--yellow)' if latest.get('confidence_score',0) >= 5 else 'var(--red)'}">{latest.get("confidence_score",0)}</div>
      <div class="metric-unit">/ 10</div>
    </div>
    <div class="metric-delta {'up' if confidence_change > 0 else 'down' if confidence_change < 0 else 'flat'}">
      {'↑ improved by ' if confidence_change > 0 else '↓ dropped by ' if confidence_change < 0 else '→ no change'}{abs(confidence_change) if confidence_change != 0 else ''} since start
    </div>
    <div class="metric-base">baseline 7 · goal 9</div>
    <div class="progress-bar-wrap">
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" style="width:{latest.get('confidence_score',0) / 9 * 100:.0f}%;background:var(--green)"></div>
      </div>
    </div>
  </div>
</div>

<!-- CHART + CONTEXT -->
<div class="main-grid">
  <div class="card">
    <div class="card-title">Progress Over Time</div>
    <div class="chart-wrap">
      <canvas id="chart"></canvas>
    </div>
  </div>
  <div class="card">
    <div class="card-title">Sessions by Type</div>
    <div class="ctx-pills">
      {context_pills if context_pills else '<p class="empty-msg">No context data yet.</p>'}
    </div>
  </div>
</div>

<!-- PATTERNS + INSIGHTS -->
<div class="bottom-grid">
  <div class="card">
    <div class="card-title">Recurring Patterns</div>
    {patterns_html}
  </div>
  <div class="card">
    <div class="card-title">Insights</div>
    <div class="insight-row">
      <div class="insight-label">Best Session</div>
      <div class="insight-val">{best.get("date","")} · {best.get("context_label","—")} · {best.get("clarity_score",0)}/10 clarity</div>
    </div>
    <div class="insight-row">
      <div class="insight-label">Most Fillers</div>
      <div class="insight-val">{most_fillers.get("date","")} · {most_fillers.get("filler_rate",0)}/100w</div>
    </div>
    <div class="insight-row">
      <div class="insight-label">Total Practice</div>
      <div class="insight-val">{total_mins} min across {len(sessions)} sessions</div>
    </div>
    <div class="insight-row">
      <div class="insight-label">Total Words Spoken</div>
      <div class="insight-val">{total_words_all} words</div>
    </div>
    <div class="insight-row">
      <div class="insight-label">Average Filler Rate</div>
      <div class="insight-val">{round(sum(filler_rates)/len(filler_rates),1) if filler_rates else 0}/100w</div>
    </div>
  </div>
</div>

<!-- REWRITES -->
<div class="card" style="margin-bottom:24px">
  <div class="card-title">How to Improve — Before & After Rewrites</div>
  {focus_html}
  {rewrites_html}
</div>

<!-- SESSION TABLE -->
<div class="table-card">
  <div class="card-title">Recent Sessions</div>
  <table>
    <thead>
      <tr>
        <th>Date & Time</th>
        <th>Context</th>
        <th class="center">Words</th>
        <th class="center">Fillers/100w</th>
        <th class="center">Clarity</th>
        <th class="center">Confidence</th>
      </tr>
    </thead>
    <tbody>{session_rows}</tbody>
  </table>
</div>

<div style="font-size:11px;color:#444;font-family:IBM Plex Mono,monospace;margin-bottom:16px;padding:0 4px">
  * short session (&lt;100 words) — scores may be less reliable &nbsp;·&nbsp; sessions &lt;50 words are excluded
</div>
<div class="footer">speech coach &nbsp;·&nbsp; local &nbsp;·&nbsp; private &nbsp;·&nbsp; phi3:mini &nbsp;·&nbsp; open source soon</div>

<script>
Chart.defaults.color = '#555555';
Chart.defaults.borderColor = '#222222';
Chart.defaults.font.family = 'IBM Plex Mono';
Chart.defaults.font.size = 11;

new Chart(document.getElementById('chart'), {{
  type: 'line',
  data: {{
    labels: {json.dumps(dates)},
    datasets: [
      {{
        label: 'Filler Rate',
        data: {json.dumps(filler_rates)},
        borderColor: '#ff4d6a',
        backgroundColor: 'rgba(255,77,106,0.05)',
        tension: 0.3, fill: true,
        pointRadius: 5, pointBackgroundColor: '#ff4d6a',
        pointBorderColor: '#0c0c0c', pointBorderWidth: 2,
        borderWidth: 2,
      }},
      {{
        label: 'Clarity /10',
        data: {json.dumps(clarity_scores)},
        borderColor: '#4d9fff',
        backgroundColor: 'rgba(77,159,255,0.05)',
        tension: 0.3, fill: true,
        pointRadius: 5, pointBackgroundColor: '#4d9fff',
        pointBorderColor: '#0c0c0c', pointBorderWidth: 2,
        borderWidth: 2,
      }},
      {{
        label: 'Confidence /10',
        data: {json.dumps(confidence_scores)},
        borderColor: '#4dffb4',
        backgroundColor: 'rgba(77,255,180,0.05)',
        tension: 0.3, fill: true,
        pointRadius: 5, pointBackgroundColor: '#4dffb4',
        pointBorderColor: '#0c0c0c', pointBorderWidth: 2,
        borderWidth: 2,
      }},
      {{
        label: 'Baseline (7.1)',
        data: Array({len(dates)}).fill(7.1),
        borderColor: '#333333',
        borderDash: [4, 4],
        pointRadius: 0,
        fill: false,
        borderWidth: 1,
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{
        position: 'bottom',
        labels: {{ boxWidth: 8, padding: 20, usePointStyle: true }}
      }},
      tooltip: {{
        backgroundColor: '#161616',
        borderColor: '#222222',
        borderWidth: 1,
        padding: 12,
      }}
    }},
    scales: {{
      x: {{ grid: {{ color: '#1a1a1a' }} }},
      y: {{ grid: {{ color: '#1a1a1a' }}, beginAtZero: true, max: 12 }}
    }}
  }}
}});

</script>
<script>
function toggleP(i) {{
  var s = document.getElementById("pshort-" + i);
  var f = document.getElementById("pfull-" + i);
  var t = document.getElementById("ptoggle-" + i);
  if (!f || !s) return;
  if (f.style.display === "none") {{
    s.style.display = "none";
    f.style.display = "inline";
    if (t) t.textContent = "show less ↑";
  }} else {{
    s.style.display = "inline";
    f.style.display = "none";
    if (t) t.textContent = "show more ↓";
  }}
}}
</script>
</body>
</html>"""

    with open(DASHBOARD_FILE, 'w') as f:
        f.write(html)
    print(f"Dashboard saved: {DASHBOARD_FILE}")
    subprocess.run(['open', str(DASHBOARD_FILE)])
    print("Opening in browser...")

def main():
    print("\n🎙️  Speech Coach — Progress Dashboard")
    sessions = load_data()
    if not sessions:
        print("No data yet. Complete at least one session in coach.py first.")
        return
    print(f"Found {len(sessions)} session(s). Building dashboard...")
    generate_dashboard(sessions)

if __name__ == "__main__":
    main()
