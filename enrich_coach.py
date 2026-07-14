#!/usr/bin/env python3
"""Enrich trainer drills with AI coach notes.

For every drill in data/trainer-drills.json that lacks a `coachNote`, build a
compact position dossier (FEN, game context, engine lines) and ask Claude
(headless `claude -p`, subscription auth via ~/.anthropic-token sourced by the
caller) to write a specific, coach-grade explanation. Results are written back
into the same JSON. Also stamps `result` (win/loss/draw) per drill by mapping
game links against the Chess.com monthly archives (cached).

Run:  python3 enrich_coach.py [--limit N] [--batch B]
Idempotent — skips drills that already have a coachNote.
"""
import json, os, re, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
DRILLS = os.path.join(ROOT, "data", "trainer-drills.json")
USERNAME = "ophirgambit"
BATCH = 8

def fetch_results_map():
    """game url -> (my result, opp result) via chess.com archives."""
    out = {}
    try:
        req = urllib.request.Request(
            f"https://api.chess.com/pub/player/{USERNAME}/games/archives",
            headers={"User-Agent": "Mozilla/5.0"})
        months = json.load(urllib.request.urlopen(req, timeout=20))["archives"]
        for m in months[-4:]:
            req = urllib.request.Request(m, headers={"User-Agent": "Mozilla/5.0"})
            for g in json.load(urllib.request.urlopen(req, timeout=30)).get("games", []):
                me = g["white"] if g["white"]["username"].lower() == USERNAME else g["black"]
                r = me.get("result", "")
                res = "won" if r == "win" else ("drew" if r in (
                    "agreed", "repetition", "stalemate", "insufficient",
                    "50move", "timevsinsufficient") else "lost")
                out[g.get("url", "")] = res
    except Exception as e:
        print(f"[warn] archives fetch failed: {e}", file=sys.stderr)
    return out

def drill_key(d):
    return f"{d.get('gid', 'x')}#{d.get('moveNum', '?')}#{d.get('played', '?')}"

def dossier(d, results):
    res = results.get(d.get("link", ""), None)
    ctx = {
        "id": drill_key(d),
        "fen": d["fen"],
        "i_play": d.get("color"),
        "opening": d.get("opening"),
        "move_number": d.get("moveNum"),
        "eval_before_my_move": d.get("evalBefore"),
        "my_move_in_game": d.get("played"),
        "eval_swing_pawns": d.get("swing"),
        "engine_best_move": d.get("best"),
        "also_acceptable": list((d.get("acceptSan") or {}).values()),
        "best_line_after": d.get("bestLine"),
        "how_my_move_gets_punished": d.get("punishLine"),
        "theme_tag": d.get("theme"),
        "opponent": d.get("title", ""),
    }
    if res:
        ctx["final_game_result_for_me"] = res
    return ctx

PROMPT = """You are a warm, sharp IM chess coach sitting right next to an adult student at the board, talking him through his OWN game. He's ~800 rapid with strong puzzle vision (~1750) but hangs things and thinks lazily in real games. Below are {n} positions where he blundered. For EACH, write a coachNote in the voice of a coach explaining it out loud to him — like you're pointing at the board together.

Make it feel like a person, not an engine readout. Talk TO him ("you", "your rook on f1", "notice that..."). Walk the LOGIC, not just the verdict — the WHY behind every claim.

Cover these beats in natural, flowing prose (no headers, no lists):
1) Point out the one thing he missed — the concrete feature: the exact loose piece, the open line/diagonal, the king's airhole, or the threat his opponent just set up. Name the square.
2) Show WHY his move fails, concretely: name the piece and square, trace the punishing sequence in words (use how_my_move_gets_punished), and say what it costs him. If he was winning (eval_before), tell him plainly what he threw away.
3) Explain what the best move actually DOES and WHY it's right — the idea and the plan, where the best line is heading over the next couple moves (use best_line_after). Give him the principle to carry forward.

Be SPECIFIC above all — always reference real squares and pieces, never vague ("keeps your pieces coordinated" is banned). Ground everything in the provided engine lines; do not invent tactics. No filler ("always check your moves", "remember to"). Don't just restate the theme tag. Warm but not gushing. 3-5 sentences, aim ~70-110 words.

Respond with ONLY a JSON object mapping each position's "id" (as a string) to its coachNote string. No markdown fences, no commentary.

POSITIONS:
{blob}"""

def call_claude(batch, results):
    blob = json.dumps([dossier(d, results) for d in batch], indent=1)
    prompt = PROMPT.format(n=len(batch), blob=blob)
    # Isolation matters: --strict-mcp-config + empty config keeps plugin MCP
    # servers (e.g. the Telegram channel) OUT of the spawned session, and the
    # disallowed tools stop any side effects. Subscription auth — do NOT
    # source ~/.anthropic-token (stale; see claude_code_heartbeat.sh).
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")}
    p = subprocess.run(
        ["claude", "-p", "--model", "claude-sonnet-5",
         "--setting-sources", "",  # no user settings → no hooks, no plugins
         "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
         "--disallowedTools", "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch,Task,TodoWrite",
         "--output-format", "text"],
        input=prompt, capture_output=True, text=True, timeout=600,
        cwd="/tmp", env=env,  # neutral cwd — no project context needed
    )
    txt = p.stdout.strip()
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise RuntimeError(f"no JSON in claude output: {txt[:300]}")
    return json.loads(m.group(0))

def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    batch_size = BATCH
    if "--batch" in sys.argv:
        batch_size = int(sys.argv[sys.argv.index("--batch") + 1])

    data = json.load(open(DRILLS))
    drills = data["drills"]
    todo = [d for d in drills if not d.get("coachNote")]
    if limit:
        todo = todo[:limit]
    if not todo:
        print("nothing to enrich")
        return
    print(f"enriching {len(todo)} drills (batch {batch_size})")
    results = fetch_results_map()

    done = 0
    for i in range(0, len(todo), batch_size):
        batch = todo[i:i + batch_size]
        try:
            notes = call_claude(batch, results)
        except Exception as e:
            print(f"[warn] batch {i//batch_size} failed: {e}", file=sys.stderr)
            continue
        for d in batch:
            note = notes.get(drill_key(d))
            if note and isinstance(note, str) and len(note) > 40:
                d["coachNote"] = note.strip()
                res = results.get(d.get("link", ""))
                if res:
                    d["result"] = res
                done += 1
        # write back after each batch — crash-safe
        json.dump(data, open(DRILLS, "w"), ensure_ascii=False)
        print(f"  batch {i//batch_size + 1}: total enriched {done}")
    print(f"done: {done}/{len(todo)}")

if __name__ == "__main__":
    main()
