# Redesign Brief — Chess Dashboard + Blunder Trainer

**For:** a design-focused Claude session ("Claude design").
**Output goes back to:** the engineering Claude session that maintains this codebase, which will implement your direction.
**Owner:** Ophir Ram — a chess improver (rapid ~810, goal 1500 by Dec 31, 2026) who uses these apps daily on his iPhone (added to home screen as a PWA) and occasionally on desktop.

---

## 1. What the product is

A two-page personal training system, plus one satellite page:

### A. Chess Dashboard (`index.html`) — the mirror
A single-scroll mobile page that answers: *"Am I on track to 1500?"*
Content order, top to bottom:
1. **Slim header** — ♟ title + a pill button linking to the Blunder Trainer.
2. **Hero strip** (royal-blue gradient) — live rapid rating (big Anton numeral), "→ 1500", % progress, days left, thin progress bar.
3. **Road to 1500 panel** (the heart of the page):
   - "TIPS" ritual pin (Threats · Ideas · Plans · Safety) + CTA to tips.html
   - 5 daily non-negotiables checklist (tap to check, strikethrough on done, 🔥 streak counter, "n/5 today")
   - Two stat tiles: blunders/game this week · blitz-free days
   - Weekly blunders-per-game bar mini-chart (6 weeks, "down and to the right wins")
   - 4 checkpoint gates (950 Sep 1 / 1100 Oct 15 / 1250 Dec 1 / 1500 Dec 31) with pace status chips (▲ ahead / ● push / ▼ behind / ✓ HIT)
4. **Key concepts card** — a short always-on reference list.
5. **Recent games** — last 5 live from Chess.com API (result icon, opponent, rating, 💥 blunder count).
6. **Quick links** + tiny footer.

### B. Blunder Trainer (`trainer.html`) — the gym
A 4-tab PWA (bottom tab bar on mobile: Home / Drill / Themes / Progress). Every drill is a real position from Ophir's own games where he blundered (nightly Stockfish pipeline). ~150+ drills and growing.

- **Home tab:** full-width "🎯 Start Drilling (N new)" CTA → rank card (chess-rank icon, XP, progress bar to next rank + a 64px daily-goal ring, 5 drills/day) → 4 stat tiles (games analyzed, blunders→drills, drill accuracy, day streak 🔥) → "Where your games are leaking" card (top blunder theme, weakest opening, danger zone) with badges.
- **Drill tab (the core screen):** task line ("You played: Ng4. Find the best move." + 3 try-pips) → chess board (green chess.com-style, cburnett SVG pieces, tap-to-move, yellow selection/last-move tints) → collapsed "ℹ️ details · Drill 3/12" row (expands to opening/date/eval chips/badges) → feedback card on answer: verdict, **"🎓 Coach's read"** (AI-written per-drill coaching prose), eval swing line, **interactive line player** ("▶ Watch the best plan" / "⚠ Watch the punishment" step engine lines on the board via a blue control bar under the board), "📘 Levy's lens" theme tip, "🧠 Think it through" checklist. Floating "Next Drill →" FAB above the tab bar when solved/failed. On phones, playing a line enters a "focus mode" that hides everything but board + controls.
- **Themes tab:** tappable cards per blunder theme (Hung Piece, Calculation Error, …) with accuracy % and position count, ordered by how often each costs him games.
- **Progress tab:** streak/attempts/accuracy tiles, hand-rolled SVG line chart (session accuracy), SVG bar chart (drills by theme), "⚠ Weakest theme this week" callout with a drill CTA.
- **Gamification:** XP per drill (10/20/30 by difficulty, combo multiplier x1.5/x2), 9 ranks Pawn→Grandmaster, daily 5-drill ring, emoji burst + toast celebrations.
- Light mode default + 🌙 dark toggle (dark theme exists and must survive the redesign).

### C. TIPS trainer (`tips.html`) — satellite
A board-free "process rep" stepper (huge Anton letter cards T-I-P-S, guided/recall modes, 3-rep warm-up). Recently built, already the most modern-feeling page. Redesign should bring the other two pages **up to and past** this level and keep all three visually unified.

---

## 2. Current visual language ("Blue Sky" theme)

- Palette: ice background `#F2F6FC`, white cards, navy text `#12213B`/`#0F2547`, blue accent `#2563EB`, royal-blue hero gradient (`#1E3A8A→#1D4ED8→#2E7CF6→#38BDF8`), amber gold `#D97706` (bright `#FFD34D` on dark), green `#059669` wins, red `#E11D48`/`#CC4B33` errors, orange `#FF8A2A` streaks.
- Type: **Anton** for display numerals/titles, system SF stack for body. tips.html also loads **Inter**.
- Shape: 12–18px radii cards, soft blue-tinted shadows, pill buttons with blue gradients, emoji as the entire icon system (🎯🔥💥🏁⚠️🧠♟).
- Trainer dark theme: chess.com-adjacent (`#0E141B` bg, `#81B64C` green).

## 3. What Ophir asked for

> "Level up the design to be **nicer on the eye, sleeker, and better motivating**."

Interpretation to design against:
1. **Nicer on the eye** — the pages read as competent-but-homemade: many card borders, mixed spacing rhythms, emoji-everywhere, uppercase-microlabels repeated a dozen times, three slightly different button systems across the three pages. It needs a coherent, confident visual system — hierarchy, restraint, polish.
2. **Sleeker** — less chrome per card, tighter vertical rhythm, fewer competing accent colors per screen, more intentional typography (Anton is loved — keep the big-numeral identity, but tame where and how often display type appears).
3. **Better motivating** — this is a *daily habit product*. The emotional job: open the app → instantly feel "here's my streak, here's today's mission, I'm on pace / I need to push." Progress (streaks, ring, gates, blunder trend, rank/XP) should feel rewarding and alive, not like a spreadsheet. Think Apple Fitness rings / Duolingo energy, but adult and chess-serious, not childish.

## 4. Hard constraints (do not violate)

- **Single-file HTML/CSS/JS per page. No build step, no frameworks, no npm.** Deliverables must be expressible as CSS + small HTML restructuring within these files. External resources: Google Fonts is OK (already used); nothing heavier.
- **Chess board stays chess.com tournament green** (`#EEEED2`/`#769656`) with the existing cburnett pieces and yellow selection tints — deliberate pattern-transfer decision. Restyle *around* the board, not the board. (Board frame/shadow treatment IS in scope.)
- **Mobile-first, iPhone PWA.** Bottom tab bar on mobile, safe-area insets, 44px+ tap targets, thumb-reachable CTAs. Desktop is secondary (max-width ~760–960px centered).
- **Dark mode must remain** in the trainer (toggle exists) — spec both themes.
- **No feature changes.** All current content/functionality stays: this is a reskin + layout/hierarchy pass, not a rebuild. Don't design new data the pipeline doesn't have.
- **Ophir's known preferences:** white & blue is his chosen identity (he explicitly rejected cream/brown and a dark-only look for the dashboard); Anton numerals are loved; no background music/sound emphasis; he dislikes clutter — he has repeatedly asked to compact/declutter (header, hero, drill screen were all slimmed at his request). Text-only minimal LinkedIn-style restraint suits him.
- Positive-only motivation psychology: streaks and progress up-signals; errors shown briefly and constructively (red exists but never dominates).

## 5. What to deliver back (so engineering can implement)

1. **Design direction statement** — 3–5 sentences naming the aesthetic (reference points welcome).
2. **Design tokens** — full CSS custom-property set: color system (light + dark), type scale (families, sizes, weights, letter-spacing), spacing scale, radii, shadows/elevation, motion (durations/easings). Prefer evolving the existing Blue Sky palette over replacing it.
3. **Component specs** for the repeating pieces: card, stat tile, pill button (primary/ghost/destructive), badge/chip, checklist row, progress bar, goal ring, streak display, gate/pace row, tab bar, section header, feedback card, toast, FAB.
4. **Per-screen guidance** (annotated, top-to-bottom) for: dashboard page, trainer Home, trainer Drill (default + feedback + line-player states), trainer Themes, trainer Progress, session-complete screen. Call out what to merge, demote, or delete visually.
5. **Motivation layer**: how streaks/ring/XP/gates should look and *feel* (micro-interactions, celebration moments, empty/zero states, "behind pace" states that spur rather than shame).
6. **Emoji/icon policy** — where emoji stay (they're part of the personality) vs. where they should be replaced by typographic or inline-SVG treatments.
7. Any **chart styling** rules for the SVG mini-charts (bars, line, ring).

Format: a single markdown spec + CSS token block(s) is ideal. Screens/HTML mockups optional but welcome. Everything must be implementable by hand-editing three HTML files.
