#!/usr/bin/env python3
"""Blunder Trainer sync — pulls new Chess.com games, finds blunders with
Stockfish, and regenerates data/trainer-drills.json for the live trainer.

Incremental: previously analyzed games are cached in data/trainer-cache.json
and skipped on later runs, so daily syncs only pay for new games.

Run:  .venv/bin/python sync_trainer.py
"""
import json, io, re, sys, os, urllib.request
from datetime import datetime, timezone
from collections import Counter, defaultdict

import chess, chess.pgn, chess.engine

USERNAME = "ophirram"
START_MONTH = "2026/05"          # ignore games before this archive month
STOCKFISH = "/opt/homebrew/bin/stockfish"
DEPTH = 14
MULTIPV = 3
BLUNDER_CP = 120                 # eval drop that counts as a blunder
ACCEPT_WINDOW_CP = 30            # alternates within this of best are accepted
LOST_CUTOFF_CP = -800            # skip blunders in already-lost positions
MAX_PER_GAME = 2
MAX_DRILLS = 150                 # newest first; keeps the page payload bounded

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(ROOT, "data", "trainer-cache.json")
OUT_PATH = os.path.join(ROOT, "data", "trainer-drills.json")

PIECE_NAMES = {chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
               chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king"}
VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5,
       chess.QUEEN: 9, chess.KING: 99}


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": f"BlunderTrainerSync/1.0 ({USERNAME})"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_games():
    months = fetch_json(f"https://api.chess.com/pub/player/{USERNAME}/games/archives")["archives"]
    months = [m for m in months if m.split("/games/")[1] >= START_MONTH]
    games = []
    for m in months:
        games += fetch_json(m).get("games", [])
    return games


def opening_name(headers):
    eco_url = headers.get("ECOUrl", "")
    if eco_url:
        name = eco_url.rstrip("/").split("/")[-1].replace("-", " ")
        return re.sub(r"\s+\d.*$", "", name).strip() or name
    return headers.get("Opening", headers.get("ECO", "Unknown"))


def opening_family(op):
    o = (op or "Unknown").lower().replace("'", "").replace("-", " ")
    table = [
        (("london", "zukertort", "chigorin", "queens pawn", "queen s pawn", "indian game", "horwitz"), "London/Queen's Pawn systems"),
        (("caro",), "Caro-Kann Defense"), (("italian", "giuoco"), "Italian Game"),
        (("ruy lopez",), "Ruy Lopez"), (("scotch",), "Scotch Game"),
        (("bishops opening",), "Bishop's Opening"), (("scandinavian",), "Scandinavian Defense"),
        (("french",), "French Defense"), (("grob",), "Grob Opening"),
        (("three knights",), "Three Knights"), (("englund",), "Englund Gambit"),
        (("polish",), "Polish Opening"), (("sicilian",), "Sicilian Defense"),
        (("kings pawn", "king s pawn", "kings knight", "damiano"), "King's Pawn (other)"),
    ]
    for keys, fam in table:
        if any(k in o for k in keys):
            return fam
    return (op or "Unknown").split(",")[0].strip()


def cp_of(score, color):
    return score.pov(color).score(mate_score=2000)


def classify_and_explain(board, best, played, swing, move_num, refut_san):
    """Theme + plain-English explanation for one drill position."""
    me = board.turn
    b2 = board.copy(); b2.push(best)
    gives_mate = b2.is_checkmate()
    gives_check = b2.is_check()
    is_capture = board.is_capture(best)
    cap_piece = board.piece_at(best.to_square) if is_capture and not board.is_en_passant(best) else None

    fork_targets = []
    if not gives_mate:
        tlist = [(p, sq) for sq in b2.attacks(best.to_square)
                 if (p := b2.piece_at(sq)) and p.color != me and p.piece_type != chess.PAWN]
        if b2.is_check():
            tlist = [(chess.Piece(chess.KING, not me), b2.king(not me))] + tlist
        if len(tlist) >= 2:
            fork_targets = tlist[:2]

    hung = False
    if refut_san and "x" in refut_san:
        bp = board.copy(); bp.push(played)
        try:
            rm = bp.parse_san(refut_san)
            hung = rm.to_square == played.to_square
        except ValueError:
            pass

    n_pieces = sum(1 for sq in chess.SQUARES
                   if (p := board.piece_at(sq)) and p.piece_type not in (chess.PAWN, chess.KING))
    if gives_mate:
        theme = "Mate Pattern"
    elif fork_targets and board.piece_at(best.from_square).piece_type in (chess.KNIGHT, chess.PAWN):
        theme = "Fork"
    elif (is_capture and cap_piece and VAL[cap_piece.piece_type] >= 3) or hung:
        theme = "Hung Piece"
    elif move_num <= 10:
        theme = "Opening Mistake"
    elif n_pieces <= 6:
        theme = "Endgame"
    elif gives_check or is_capture:
        theme = "Missed Tactic"
    else:
        theme = "Calculation Error"

    best_san = board.san(best)
    played_san = board.san(played)
    parts = []
    if gives_mate:
        parts.append(f"{best_san} is checkmate on the spot — the king has no escape squares.")
    elif fork_targets:
        tdesc = " and ".join(f"the {PIECE_NAMES[p.piece_type]} on {chess.square_name(sq)}" for p, sq in fork_targets)
        parts.append(f"{best_san} forks {tdesc} — one of them falls next move.")
    elif is_capture and cap_piece:
        parts.append(f"{best_san} simply wins the {PIECE_NAMES[cap_piece.piece_type]} on "
                     f"{chess.square_name(best.to_square)} — it wasn't adequately defended.")
    elif gives_check:
        parts.append(f"{best_san} gives check and seizes the initiative — your opponent must "
                     f"respond to the threat before doing anything else.")
    else:
        parts.append(f"{best_san} was the move — it keeps your pieces coordinated and avoids "
                     f"the tactic that punished your game move.")
    if hung:
        parts.append(f"In the game, {played_san} left that piece hanging: after {refut_san} it's simply lost.")
    elif refut_san:
        parts.append(f"In the game, {played_san} ran into {refut_san}, costing about {swing} pawns of advantage.")
    else:
        parts.append(f"In the game, {played_san} cost about {swing} pawns of advantage.")
    return theme, " ".join(parts)


def analyze_game(engine, g):
    """Return (drills, meta) for one chess.com game json."""
    pgn = g.get("pgn")
    if not pgn:
        return [], None
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        return [], None
    h = game.headers
    me = chess.WHITE if h.get("White", "").lower() == USERNAME else chess.BLACK
    raw_result = h.get("Result", "*")
    result = {"1-0": "Win" if me == chess.WHITE else "Loss",
              "0-1": "Loss" if me == chess.WHITE else "Win"}.get(raw_result, "Draw")
    opp = h.get("Black" if me == chess.WHITE else "White", "?")
    opp_elo = h.get("BlackElo" if me == chess.WHITE else "WhiteElo", "?")
    opening = opening_name(h)
    date = (h.get("UTCDate", "") or "").replace(".", "-")
    meta = {"opening": opening, "family": opening_family(opening), "result": result,
            "color": "White" if me == chess.WHITE else "Black", "date": date,
            "title": f"vs {opp} ({opp_elo}) — {opening}", "link": g.get("url", "")}

    limit = chess.engine.Limit(depth=DEPTH)
    board = game.board()
    found = []
    for node in game.mainline():
        move = node.move
        if board.turn == me:
            infos = engine.analyse(board, limit, multipv=MULTIPV)
            best_info = infos[0]
            best = best_info["pv"][0]
            ev_before = cp_of(best_info["score"], me)
            after = board.copy(); after.push(move)
            if after.is_game_over():
                ev_after = 2000 if after.is_checkmate() else 0
                refut_san = None
            else:
                info2 = engine.analyse(after, limit)
                ev_after = cp_of(info2["score"], me)
                refut_san = after.san(info2["pv"][0]) if info2.get("pv") else None
            drop = ev_before - ev_after
            if drop >= BLUNDER_CP and move != best and ev_before > LOST_CUTOFF_CP:
                accept, accept_san = [], {}
                for inf in infos:
                    if not inf.get("pv"):
                        continue
                    mv = inf["pv"][0]
                    if ev_before - cp_of(inf["score"], me) <= ACCEPT_WINDOW_CP:
                        accept.append(mv.uci())
                        accept_san[mv.uci()] = board.san(mv)
                swing = round(drop / 100, 1)
                theme, expl = classify_and_explain(board, best, move, swing,
                                                   board.fullmove_number, refut_san)
                found.append({
                    "fen": board.fen(), "played": board.san(move), "playedUci": move.uci(),
                    "best": board.san(best), "bestUci": best.uci(),
                    "accept": accept or [best.uci()], "acceptSan": accept_san,
                    "swing": swing, "moveNum": board.fullmove_number,
                    "theme": theme,
                    "difficulty": "Easy" if swing < 1.5 else ("Medium" if swing <= 3.0 else "Hard"),
                    "explanation": expl,
                    "hintPiece": PIECE_NAMES[board.piece_at(best.from_square).piece_type].capitalize(),
                })
        board.push(move)
    found.sort(key=lambda d: -d["swing"])
    return found[:MAX_PER_GAME], meta


def main():
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    cache = {"games": {}}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)

    games = fetch_games()
    by_id = {}
    for g in games:
        m = re.search(r"/(\d+)$", g.get("url", ""))
        if m:
            by_id[m.group(1)] = g
    new_ids = [gid for gid in by_id if gid not in cache["games"]]
    print(f"games total: {len(by_id)}, cached: {len(by_id) - len(new_ids)}, new: {len(new_ids)}")

    if new_ids:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH)
        engine.configure({"Threads": max(2, (os.cpu_count() or 4) - 2), "Hash": 256})
        try:
            for n, gid in enumerate(new_ids, 1):
                try:
                    drills, meta = analyze_game(engine, by_id[gid])
                except Exception as e:
                    print(f"  [{n}/{len(new_ids)}] {gid}: FAILED {e}", file=sys.stderr)
                    continue
                cache["games"][gid] = {"meta": meta, "drills": drills}
                print(f"  [{n}/{len(new_ids)}] {gid}: {len(drills)} drills")
        finally:
            engine.quit()
        with open(CACHE_PATH, "w") as f:
            json.dump(cache, f)

    # ---- assemble drill bank + stats from the full cache ----
    entries = [(gid, e) for gid, e in cache["games"].items() if e.get("meta")]
    entries.sort(key=lambda x: x[1]["meta"].get("date", ""), reverse=True)

    drills = []
    for gid, e in entries:
        for d in e["drills"]:
            drills.append({**d, "gid": gid, "opening": e["meta"]["opening"],
                           "color": e["meta"]["color"], "date": e["meta"]["date"],
                           "title": e["meta"]["title"], "link": e["meta"]["link"]})
    drills = drills[:MAX_DRILLS]

    theme_counts = Counter(d["theme"] for d in drills)
    fam = defaultdict(lambda: [0, 0, 0])
    for gid, e in entries:
        i = {"Win": 0, "Loss": 1, "Draw": 2}[e["meta"]["result"]]
        fam[e["meta"]["family"]][i] += 1
    openings = [{"family": k, "n": sum(v), "w": v[0], "l": v[1], "d": v[2]}
                for k, v in fam.items()]
    weak = [o for o in openings if o["n"] >= 5]
    weakest = min(weak, key=lambda o: o["w"] / o["n"]) if weak else None
    mid = sum(1 for d in drills if 11 <= d["moveNum"] <= 25)

    payload = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "username": USERNAME,
        "gamesAnalyzed": len(entries),
        "stats": {
            "themes": dict(theme_counts.most_common()),
            "themeOrder": [t for t, _ in theme_counts.most_common()],
            "topTheme": theme_counts.most_common(1)[0][0] if theme_counts else "—",
            "weakestOpening": (f"{weakest['family']} ({round(100 * weakest['w'] / weakest['n'])}% "
                               f"over {weakest['n']} games)") if weakest else "—",
            "openings": sorted(openings, key=lambda o: -o["n"]),
            "midgamePct": round(100 * mid / len(drills)) if drills else 0,
        },
        "drills": drills,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f)
    print(f"wrote {OUT_PATH}: {len(drills)} drills from {len(entries)} games")


if __name__ == "__main__":
    main()
