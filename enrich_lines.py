#!/usr/bin/env python3
"""One-off: add engine lines (bestLine / punishLine) to every existing drill in
data/trainer-drills.json and data/trainer-cache.json. Future drills get lines
from sync_trainer.py directly."""
import json, os
import chess, chess.engine

ROOT = os.path.dirname(os.path.abspath(__file__))
DEPTH = 16

def san_line(board, moves, limit):
    out, b = [], board.copy()
    for mv in moves[:limit]:
        out.append(b.san(mv))
        b.push(mv)
    return out

def lines_for(engine, fen, played_uci):
    board = chess.Board(fen)
    limit = chess.engine.Limit(depth=DEPTH)
    info = engine.analyse(board, limit)
    best_line = san_line(board, info.get("pv", []), 6)
    after = board.copy()
    after.push(chess.Move.from_uci(played_uci))
    punish_line = []
    if not after.is_game_over():
        info2 = engine.analyse(after, limit)
        punish_line = san_line(after, info2.get("pv", []), 4)
    return best_line, punish_line

def main():
    engine = chess.engine.SimpleEngine.popen_uci("/opt/homebrew/bin/stockfish")
    engine.configure({"Threads": max(2, (os.cpu_count() or 4) - 2), "Hash": 256})

    drills_path = os.path.join(ROOT, "data", "trainer-drills.json")
    cache_path = os.path.join(ROOT, "data", "trainer-cache.json")
    payload = json.load(open(drills_path))
    cache = json.load(open(cache_path))

    memo = {}
    for n, d in enumerate(payload["drills"], 1):
        k = d["fen"] + "|" + d["playedUci"]
        if k not in memo:
            memo[k] = lines_for(engine, d["fen"], d["playedUci"])
        d["bestLine"], d["punishLine"] = memo[k]
        print(f"[{n}/{len(payload['drills'])}] {d['best']}: {' '.join(d['bestLine'])}")

    for gid, e in cache["games"].items():
        for d in e.get("drills", []):
            k = d["fen"] + "|" + d["playedUci"]
            if k not in memo:
                memo[k] = lines_for(engine, d["fen"], d["playedUci"])
            d["bestLine"], d["punishLine"] = memo[k]

    engine.quit()
    json.dump(payload, open(drills_path, "w"))
    json.dump(cache, open(cache_path, "w"))
    print("done — lines written to drills + cache")

if __name__ == "__main__":
    main()
