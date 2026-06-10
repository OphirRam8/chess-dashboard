#!/usr/bin/env python3
"""Reconcile bestLine with the stored best move: deeper analysis sometimes
prefers a different move than the depth-14 'best' the app checks against.
Re-extract the PV constrained to start with the stored best move."""
import json, os
import chess, chess.engine

ROOT = os.path.dirname(os.path.abspath(__file__))

def main():
    drills_path = os.path.join(ROOT, "data", "trainer-drills.json")
    cache_path = os.path.join(ROOT, "data", "trainer-cache.json")
    payload = json.load(open(drills_path))
    cache = json.load(open(cache_path))

    engine = chess.engine.SimpleEngine.popen_uci("/opt/homebrew/bin/stockfish")
    engine.configure({"Threads": max(2, (os.cpu_count() or 4) - 2), "Hash": 256})
    limit = chess.engine.Limit(depth=16)

    memo = {}
    def fixed_line(fen, best_uci):
        k = fen + "|" + best_uci
        if k in memo:
            return memo[k]
        board = chess.Board(fen)
        best = chess.Move.from_uci(best_uci)
        info = engine.analyse(board, limit, root_moves=[best])
        out, b = [], board.copy()
        for mv in info.get("pv", [])[:6]:
            out.append(b.san(mv))
            b.push(mv)
        memo[k] = out
        return out

    fixed = 0
    for d in payload["drills"]:
        if not d.get("bestLine") or d["bestLine"][0] != d["best"]:
            d["bestLine"] = fixed_line(d["fen"], d["bestUci"])
            fixed += 1
    for gid, e in cache["games"].items():
        for d in e.get("drills", []):
            if not d.get("bestLine") or d["bestLine"][0] != d["best"]:
                d["bestLine"] = fixed_line(d["fen"], d["bestUci"])

    engine.quit()
    json.dump(payload, open(drills_path, "w"))
    json.dump(cache, open(cache_path, "w"))
    print(f"reconciled {fixed} drill lines")

if __name__ == "__main__":
    main()
