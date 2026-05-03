# 🎙️ Speech Coach

A free, fully local, private AI speech improvement tool for macOS.

**No cloud. No API costs. No data leaves your Mac.**

Built by [Jitesh Jalan](https://github.com/jiteshjalan) using Muesli + Ollama + Phi3 Mini + Python.

---

## The Problem

Most people don't realize how they actually sound when they speak. Filler words, incomplete thoughts, hedging language, jumping between ideas — these habits quietly undermine how confident and clear you come across in meetings, pitches, and conversations.

Existing speech coaching tools are either expensive, cloud-based, or only analyze formal presentations. There was nothing that worked passively in the background, analyzed your everyday thinking out loud, and gave you honest feedback — privately, for free, on your own machine.

So I built one.

---

## What It Does

- Captures your voice via Muesli (local Whisper-based dictation on macOS)
- Collects everything you say into a session silently in the background
- When you type `done`, analyzes the full session with a local LLM (Phi3 Mini via Ollama)
- Auto-detects what type of conversation it was — pitch, brainstorm, mentor session, rubber ducking, thinking out loud, decision making, feedback, or learning
- Gives you structured feedback on filler words, thinking clarity, confidence, and recurring patterns
- Shows before and after rewrites of your weakest sentences so you know exactly how to say it better
- Gives you one specific focus to practice tomorrow
- Saves structured JSON data after every session
- Generates an HTML progress dashboard showing your improvement over time with charts

---

## Your Baselines (Day 1)

| Metric | Baseline | Goal |
|---|---|---|
| Filler rate | 7.1 per 100 words | < 3 per 100 words |
| Thinking clarity | 6/10 | 8/10 |
| Confidence | 7/10 | 9/10 |

---

## Stack

| Component | Tool |
|---|---|
| Voice to text | [Muesli](https://github.com/pHequals7/muesli) — local Whisper on Apple Silicon |
| Local LLM | [Ollama](https://ollama.com) + Phi3 Mini (~2GB RAM) |
| Language | Python 3 |
| Storage | JSON + SQLite (Muesli's DB) |
| Dashboard | HTML + Chart.js |
| Platform | macOS (Apple Silicon M1+) |

---

## Why Fully Local?

- Your voice data never leaves your machine
- No API costs — completely free after setup
- Works offline
- You own everything — the data, the model, the reports
- Phi3 Mini runs fast on Apple Silicon Metal GPU

---

## Features

- **Auto session collection** — runs in the background, captures every Muesli dictation
- **Auto context detection** — detects pitch vs brainstorm vs mentor session automatically
- **Filler word tracking** — counts "right", "like", "you know", "I mean" and more
- **Thinking clarity score** — 1-10 score with explanation
- **Confidence score** — flags hedging language like "I think maybe", "sort of", "kind of"
- **Before & after rewrites** — takes your weakest sentences and shows you the better version
- **Today's focus** — one specific thing to practice tomorrow, not a generic list
- **Recurring patterns** — habits that show up across multiple sessions
- **Progress dashboard** — HTML dashboard with charts, session history, context breakdown, insights
- **Short session detection** — flags sessions under 100 words as less reliable
- **2 hour auto-report** — generates report automatically if you forget to type done
- **Session types** — thinking, pitch, mentor, rubber ducking, brainstorm, feedback, learning, decision

---

## Install

**Requirements:**
- macOS 14+ on Apple Silicon (M1/M2/M3)
- [Muesli](https://github.com/pHequals7/muesli) installed and running
- Homebrew

```bash
git clone https://github.com/jiteshjalan/Speech-Coach.git
cd Speech-Coach
chmod +x setup.sh && ./setup.sh
```

The setup script will:
1. Install Ollama via Homebrew
2. Pull Phi3 Mini model (~2GB download)
3. Create a Python virtual environment
4. Install required packages
5. Copy scripts to `~/SpeechCoach/`

---

## How to Use

**Terminal 1 — Start Ollama:**
```bash
ollama serve
```

**Terminal 2 — Start Speech Coach:**
```bash
source ~/SpeechCoach/venv/bin/activate
python3 ~/SpeechCoach/coach.py
```

Now speak into Muesli normally throughout your day. When you're done with a session:

```
done        # generates full session report + saves data + opens dashboard
progress    # regenerates and opens dashboard anytime
Ctrl+C      # generates final report and stops
```

---

## Session Types Auto-Detected

| Type | When |
|---|---|
| 💭 Thinking Out Loud | Processing thoughts, no clear audience |
| 🚀 Pitch | Explaining a product or idea to convince someone |
| 🎓 Mentor | Answering questions, receiving guidance |
| 🦆 Rubber Ducking | Talking through a technical problem to solve it |
| ⚡ Brainstorm | Free flowing idea generation |
| 📋 Feedback | Giving critique or review |
| 📚 Learning | Processing something new you just learned |
| ⚖️ Decision | Thinking through a choice, weighing options |

---

## File Structure

```
~/SpeechCoach/
├── coach.py              # main session analyzer — run this daily
├── progress.py           # dashboard generator
├── venv/                 # python virtual environment
├── reports/              # text reports per session (gitignored)
├── progress_data.json    # all session data (gitignored)
└── dashboard.html        # generated progress dashboard (gitignored)
```

---

## Dashboard

The progress dashboard shows:
- Filler rate, clarity, and confidence trends over time
- Progress bars toward your goals
- Sessions breakdown by type
- Recurring patterns across all sessions (clickable to expand)
- Before and after rewrites from your latest session
- Today's focus
- Best session, most fillers, total practice time
- Full session history table with color coded scores

---

## Roadmap

- [x] V1 — Local speech analysis (filler words, clarity, confidence)
- [x] V1 — Session mode with manual and auto trigger
- [x] V1 — Auto context detection across 8 session types
- [x] V1 — Before and after rewrites with explanation
- [x] V1 — Progress tracking with HTML dashboard
- [x] V1 — Short session flagging
- [ ] V1.5 — Vocabulary intelligence (range score, word frequency, synonym suggestions)
- [ ] V1.5 — Daily challenge system
- [ ] V1.5 — Weekly PDF summary
- [ ] V2 — Meeting mode (analyze full conversations)
- [ ] V2 — Gemini audio layer for tone, accent, and pace
- [ ] V3 — 30 day streak tracking
- [ ] V3 — Personal speech profile after 30 sessions
- [ ] V3 — Community benchmarks (anonymous)

---

## Contributing

Contributions welcome. Open an issue before submitting large PRs. This is early stage — bugs exist, prompts need tuning, and the model sometimes misformats output. If you find issues please report them.

---

## CV One-liner

> "Built a fully local, open-source AI speech coaching tool using Python, Ollama, and Whisper that analyzes filler words, thinking clarity, and confidence patterns from voice transcriptions with a real-time progress dashboard."

---

## License

MIT — free and open source.

---

*Built on Apple Silicon M1 · Phi3 Mini · Muesli · Ollama · Python*
