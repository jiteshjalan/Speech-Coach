#!/usr/bin/env python3
"""
SPEECH COACH - Session Analyzer with Auto Context Detection
Collects Muesli dictations, auto-detects conversation type,
analyzes with Phi3 Mini, saves structured JSON data.

RUN:
  source ~/SpeechCoach/venv/bin/activate
  python3 ~/SpeechCoach/coach.py

Commands:
  done      → generate session report
  progress  → open dashboard in browser
  Ctrl+C    → generate final report and stop
"""

import time
import threading
import requests
import sqlite3
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

# ============================================
# CONFIG
# ============================================

MUESLI_DB = Path.home() / "Library/Application Support/Muesli/muesli.db"
REPORTS_DIR = Path.home() / "SpeechCoach/reports"
DATA_FILE = Path.home() / "SpeechCoach/progress_data.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3:mini"
SESSION_DURATION = 2 * 60 * 60
POLL_INTERVAL = 10

# ============================================
# CONTEXT DETECTION PROMPT
# ============================================

CONTEXT_DETECTION_PROMPT = """You are analyzing a spoken transcript to determine what type of conversation it is.

Choose EXACTLY ONE of these context types:
- thinking: casual thinking out loud, processing thoughts, no clear audience
- pitch: explaining a product, idea, or concept to convince someone
- mentor: answering questions, receiving guidance, learning from someone senior
- rubber_ducking: talking through a technical or product problem to solve it
- brainstorm: free flowing idea generation, exploring possibilities
- feedback: giving critique or review of someone else's work
- learning: processing something new, explaining what was just learned
- decision: thinking through a choice, weighing options

Reply with ONLY the context type word. Nothing else. No explanation.

TRANSCRIPT:
"""

# ============================================
# CONTEXT-SPECIFIC COACH PROMPTS
# ============================================

CONTEXT_PROMPTS = {
    "thinking": """You are analyzing a "thinking out loud" session.
Focus on: Did they reach any clear conclusions? Are thoughts organized or scattered?
Is there a logical thread or just random jumping? Are they going in circles?""",

    "pitch": """You are analyzing a pitch or explanation session.
Focus on: Is the core idea clear in the first 30 seconds? Is there conviction in the delivery?
Are they over-explaining or under-explaining? Does it build logically to a point?
Would someone unfamiliar with the topic understand it?""",

    "mentor": """You are analyzing a mentor or coaching session (the speaker's side only).
Focus on: Are they asking clear questions? Do they explain their situation with enough context?
Are they receptive and thoughtful in responses? Do they sound confident or uncertain?
Are they making the most of the mentor's time?""",

    "rubber_ducking": """You are analyzing a rubber ducking session — talking through a problem.
Focus on: Did they actually define the problem clearly at the start?
Did they explore multiple angles or get stuck on one? Did they reach any insight or conclusion?
Is the thinking systematic or chaotic?""",

    "brainstorm": """You are analyzing a brainstorming session.
Focus on: How many distinct ideas were generated? Did they build on ideas or abandon them?
Was there creative energy or did it feel forced? Did they evaluate too early (killing ideas before exploring)?""",

    "feedback": """You are analyzing a feedback-giving session.
Focus on: Is the feedback specific and actionable or vague? Is there a clear structure (what works, what doesn't)?
Do they back up critique with reasoning? Is the tone constructive?""",

    "learning": """You are analyzing a learning/processing session.
Focus on: Can they explain the concept clearly in their own words? Do they make good analogies?
Do they identify gaps in their understanding? Is the explanation coherent to someone unfamiliar?""",

    "decision": """You are analyzing a decision-making session.
Focus on: Did they clearly define the decision to be made? Did they consider multiple options?
Did they actually reach a decision or just go in circles? Was the reasoning sound?"""
}

CONTEXT_LABELS = {
    "thinking": "Thinking Out Loud",
    "pitch": "Pitch / Explanation",
    "mentor": "Mentor Session",
    "rubber_ducking": "Rubber Ducking",
    "brainstorm": "Brainstorm",
    "feedback": "Feedback Giving",
    "learning": "Learning / Processing",
    "decision": "Decision Making"
}

# ============================================
# BASE COACH PROMPT
# ============================================

BASE_PROMPT = """You are a direct, neutral speech and communication coach.
Analyze this full session of spoken transcripts. Be honest, strict, specific. No sugarcoating.

{context_guidance}

Also analyze for:
1. FILLER WORDS - Count total: "right", "like", "you know", "basically", "literally", "I mean", "okay so", "so", "um", "uh"
2. INCOMPLETE THOUGHTS - Ideas that start but don't finish
3. THINKING CLARITY - Can a listener follow the logic?
4. CONFIDENCE LANGUAGE - Hedging: "I think maybe", "I feel like", "sort of", "kind of"
5. PATTERNS - Recurring habits across the session

Output in this EXACT format:

SESSION TYPE: {context_label}

SESSION SUMMARY:
- Total dictations analyzed: X
- Total words spoken: X
- Session duration: X minutes

CONTEXT ASSESSMENT:
[2-3 sentences specific to the session type — was this a good pitch? did they solve the problem? did they reach a decision?]

FILLER WORD COUNT:
- "right": X times
- "like": X times
- "you know": X times
- "basically": X times
- "I mean": X times
- "um": X times
- "uh": X times
TOTAL FILLERS: X
FILLER RATE: X fillers per 100 words

INCOMPLETE THOUGHTS:
- [Quote] -> [What was missing]

THINKING CLARITY SCORE: X/10
[Two sentence explanation]

CONFIDENCE SCORE: X/10
[Two sentence explanation]

TOP PATTERNS:
1. [Pattern — max 10 words]
2. [Pattern — max 10 words]
3. [Pattern — max 10 words]

DID YOU IMPROVE DURING THE SESSION?
[Honest assessment — compare early vs late dictations]

TOP 3 THINGS TO WORK ON NEXT SESSION:
1. [Specific, actionable]
2. [Specific, actionable]
3. [Specific, actionable]

BEFORE & AFTER REWRITES:
Pick 3 actual sentences from the transcript that were weak — unclear, filled with hedging, or incomplete. Rewrite each one to show exactly how it should have been said. Be specific and use the speaker's own words and ideas.

REWRITE 1:
SAID: [exact quote from transcript]
BETTER: [rewritten version — direct, clear, confident]
WHY: [one sentence explanation of what changed]

REWRITE 2:
SAID: [exact quote from transcript]
BETTER: [rewritten version — direct, clear, confident]
WHY: [one sentence explanation of what changed]

REWRITE 3:
SAID: [exact quote from transcript]
BETTER: [rewritten version — direct, clear, confident]
WHY: [one sentence explanation of what changed]

TODAY'S FOCUS:
[Single most important thing to practice tomorrow. One sentence. Very specific. Not generic advice.]

ONE THING YOU DID WELL:
[Honest — if nothing, say so]
"""

# ============================================
# STATE
# ============================================

session_dictations = []
last_id = 0
session_start = datetime.now()
generate_report_flag = threading.Event()
stop_flag = threading.Event()

# ============================================
# DB
# ============================================

def get_starting_id() -> int:
    try:
        conn = sqlite3.connect(str(MUESLI_DB))
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id) FROM dictations")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result[0] else 0
    except:
        return 0


def get_new_dictations(since_id: int) -> list:
    results = []
    try:
        conn = sqlite3.connect(str(MUESLI_DB))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, raw_text, created_at FROM dictations WHERE id > ? AND raw_text != '' ORDER BY id ASC",
            (since_id,)
        )
        for row in cursor.fetchall():
            results.append({'id': row[0], 'text': row[1], 'timestamp': row[2]})
        conn.close()
    except Exception as e:
        print(f"DB error: {e}")
    return results

# ============================================
# CONTEXT DETECTION
# ============================================

def detect_context(dictations: list) -> str:
    """Ask Phi3 to detect what type of session this is."""
    sample = " ".join([d['text'] for d in dictations[:5]])  # use first 5 dictations
    prompt = CONTEXT_DETECTION_PROMPT + f'"{sample}"'

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60
        )
        result = response.json().get("response", "thinking").strip().lower()
        # Clean up response — take first word only
        result = result.split()[0] if result.split() else "thinking"
        # Validate against known contexts
        if result not in CONTEXT_PROMPTS:
            result = "thinking"
        return result
    except:
        return "thinking"

# ============================================
# ANALYSIS
# ============================================

def analyze_session(dictations: list) -> tuple:
    """Detect context then analyze session. Returns (analysis, context)."""

    print("🔍 Detecting session type...")
    context = detect_context(dictations)
    context_label = CONTEXT_LABELS.get(context, "Thinking Out Loud")
    print(f"📌 Detected: {context_label}")

    full_text = ""
    for i, d in enumerate(dictations):
        full_text += f"\n[Dictation {i+1}]:\n{d['text']}\n"

    total_words = sum(len(d['text'].split()) for d in dictations)
    duration = (datetime.now() - session_start).seconds // 60

    prompt = BASE_PROMPT.format(
        context_guidance=CONTEXT_PROMPTS[context],
        context_label=context_label
    ) + f"""
SESSION INFO:
- Number of dictations: {len(dictations)}
- Total words: {total_words}
- Duration: {duration} minutes

FULL SESSION TRANSCRIPTS:
{full_text}
"""

    try:
        print("⏳ Analyzing... (1-2 minutes)\n")
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=300
        )
        return response.json().get("response", "No response."), context
    except Exception as e:
        return f"Ollama error: {e}", context

# ============================================
# PARSE + SAVE
# ============================================

def parse_analysis(analysis: str, dictations: list, context: str) -> dict:
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "timestamp": datetime.now().isoformat(),
        "context": context,
        "context_label": CONTEXT_LABELS.get(context, "Unknown"),
        "total_dictations": len(dictations),
        "total_words": sum(len(d['text'].split()) for d in dictations),
        "duration_minutes": (datetime.now() - session_start).seconds // 60,
        "filler_rate": 0.0,
        "total_fillers": 0,
        "clarity_score": 0,
        "confidence_score": 0,
        "filler_breakdown": {},
        "patterns": [],
        "improvements": [],
        "raw_analysis": analysis
    }

    filler_rate_match = re.search(r'FILLER RATE:\s*([\d.]+)', analysis)
    if filler_rate_match:
        data["filler_rate"] = float(filler_rate_match.group(1))
    else:
        # Fallback: calculate from total fillers and words
        total_f = re.search(r'TOTAL FILLERS:\s*(\d+)', analysis)
        if total_f and data["total_words"] > 0:
            data["filler_rate"] = round(int(total_f.group(1)) / data["total_words"] * 100, 1)

    total_fillers_match = re.search(r'TOTAL FILLERS:\s*(\d+)', analysis)
    if total_fillers_match:
        data["total_fillers"] = int(total_fillers_match.group(1))

    # Flexible clarity score extraction — handles "5/10", "5 out of 10", "around 5/10"
    clarity_match = re.search(r'THINKING CLARITY SCORE[^\n]*?[:\s]+(\d+)\s*/\s*10', analysis, re.IGNORECASE)
    if not clarity_match:
        clarity_match = re.search(r'clarity[^\n]*?(\d+)\s*/\s*10', analysis, re.IGNORECASE)
    if clarity_match:
        data["clarity_score"] = int(clarity_match.group(1))

    # Flexible confidence score extraction
    confidence_match = re.search(r'CONFIDENCE SCORE[^\n]*?[:\s]+(\d+)\s*/\s*10', analysis, re.IGNORECASE)
    if not confidence_match:
        confidence_match = re.search(r'confidence[^\n]*?(\d+)\s*/\s*10', analysis, re.IGNORECASE)
    if confidence_match:
        data["confidence_score"] = int(confidence_match.group(1))

    filler_pattern = re.findall(r'"([\w\s]+)":\s*(\d+) times', analysis)
    for word, count in filler_pattern:
        data["filler_breakdown"][word.strip()] = int(count)

    pattern_matches = re.findall(r'^\d+\.\s+(.+)$', analysis, re.MULTILINE)
    if pattern_matches:
        data["patterns"] = pattern_matches[:3]
        data["improvements"] = pattern_matches[3:6] if len(pattern_matches) > 3 else []

    # Extract before/after rewrites
    rewrites = []
    rewrite_blocks = re.findall(
        r'REWRITE \d+:\s*\nSAID:\s*(.+?)\nBETTER:\s*(.+?)\nWHY:\s*(.+?)(?=\nREWRITE|\nTODAY|\nONE THING|$)',
        analysis, re.DOTALL
    )
    for said, better, why in rewrite_blocks:
        rewrites.append({
            "said": said.strip().strip('"'),
            "better": better.strip().strip('"'),
            "why": why.strip()
        })
    data["rewrites"] = rewrites

    # Extract today's focus — flexible match handles variations like "TODAY'S FOCUS (one sentence):"
    focus_match = re.search(r"TODAY['']S FOCUS[^\n]*?:\s*\n?(.+?)(?=\nONE THING|\nBEFORE|$)", analysis, re.DOTALL | re.IGNORECASE)
    if focus_match:
        data["todays_focus"] = focus_match.group(1).strip().split("\n")[0].strip()
    else:
        data["todays_focus"] = ""

    return data


def save_progress_data(session_data: dict):
    all_data = []
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r') as f:
                all_data = json.load(f)
        except:
            all_data = []
    all_data.append(session_data)
    with open(DATA_FILE, 'w') as f:
        json.dump(all_data, f, indent=2)
    print(f"✅ Progress data saved ({len(all_data)} total sessions)")


def save_text_report(analysis: str, dictations: list, context: str, timestamp: str):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = REPORTS_DIR / f"session_{context}_{timestamp}.txt"
    with open(filepath, 'w') as f:
        f.write("=" * 55 + "\n")
        f.write("SPEECH COACH — SESSION REPORT\n")
        f.write(f"Type: {CONTEXT_LABELS.get(context, 'Unknown')}\n")
        f.write(f"Date: {datetime.now().strftime('%B %d, %Y')}\n")
        f.write(f"Session: {session_start.strftime('%I:%M %p')} → {datetime.now().strftime('%I:%M %p')}\n")
        f.write("=" * 55 + "\n\n")
        f.write("TRANSCRIPTS:\n")
        f.write("-" * 30 + "\n")
        for i, d in enumerate(dictations):
            f.write(f"\n[{i+1}] {d['text']}\n")
        f.write("\n" + "=" * 55 + "\n")
        f.write("ANALYSIS:\n")
        f.write("=" * 55 + "\n\n")
        f.write(analysis + "\n")
    print(f"📄 Report saved: {filepath}")


def run_report():
    global session_dictations, session_start

    if not session_dictations:
        print("\n⚠️  No dictations yet. Keep speaking!\n")
        return

    print(f"\n📊 Processing {len(session_dictations)} dictations...")
    analysis, context = analyze_session(session_dictations)

    print("\n" + "=" * 55)
    print("🎙️  SESSION REPORT")
    print("=" * 55)
    print(analysis)
    print("=" * 55 + "\n")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_text_report(analysis, session_dictations, context, timestamp)
    session_data = parse_analysis(analysis, session_dictations, context)
    save_progress_data(session_data)

    print("\nType 'progress' to open dashboard, or keep speaking for next session.\n")

    # Reset session
    session_dictations = []
    session_start = datetime.now()

# ============================================
# INPUT LISTENER
# ============================================

def listen_for_commands():
    while not stop_flag.is_set():
        try:
            user_input = input().strip().lower()
            if user_input == 'done':
                generate_report_flag.set()
            elif user_input == 'progress':
                print("🔄 Regenerating dashboard...")
                progress_script = Path.home() / "SpeechCoach/progress.py"
                if progress_script.exists():
                    subprocess.run(['python3', str(progress_script)])
                else:
                    print("progress.py not found in ~/SpeechCoach/")
        except EOFError:
            break

# ============================================
# MAIN
# ============================================

def main():
    global last_id, session_dictations, session_start

    print("\n🎙️  Speech Coach — Session Mode")
    print("=" * 40)
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Reports → {REPORTS_DIR}")
    print("Commands: 'done' → report | 'progress' → dashboard")
    print("=" * 40 + "\n")

    last_id = get_starting_id()
    session_start = datetime.now()
    print(f"Session started at {session_start.strftime('%I:%M %p')} (entry ID: {last_id})\n")
    print("Speak into Muesli. I'm collecting everything...\n")

    input_thread = threading.Thread(target=listen_for_commands, daemon=True)
    input_thread.start()

    last_auto_report = time.time()

    while True:
        try:
            new_entries = get_new_dictations(last_id)
            for entry in new_entries:
                text = entry['text'].strip()
                if len(text.split()) >= 5:
                    session_dictations.append(entry)
                    last_id = entry['id']
                    total = len(session_dictations)
                    print(f"📝 Captured #{total} ({len(text.split())} words) — type 'done' for report")

            if generate_report_flag.is_set():
                generate_report_flag.clear()
                run_report()
                last_auto_report = time.time()

            if time.time() - last_auto_report >= SESSION_DURATION:
                print("\n⏰ 2 hours — auto generating report...")
                run_report()
                last_auto_report = time.time()

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n\nStopping — generating final report...")
            if session_dictations:
                run_report()
            stop_flag.set()
            print("👋 Speech Coach stopped. Keep practicing!")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
