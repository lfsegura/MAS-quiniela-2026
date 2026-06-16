# CLAUDE.md — Quiniela Mundial 2026 (project handoff)

Context and working guide for an AI assistant (Claude Code) helping run a FIFA World Cup 2026
prediction pool ("quiniela") among 6 friends. Read this fully before making changes.

---

## 1. What this project is

- A **winner-take-all** prediction pool for the 2026 World Cup (48 teams, 12 groups, hosts USA/Mexico/Canada).
- 6 participants each submit a completed bracket (predicted scores for every match, group stage → final).
- Scoring is automatic via a self-calculating Excel workbook; we also built a web **tracker** and an
  auto-updating **public page**.
- Owner/organizer: **LF — Luis Felipe Segura** (lf.segura@incode.com), Field CTO at Incode. LF is also a participant.

### Pool rules (important)
- Originally paid top 3 (50/30/20); **rules changed to a single winner (winner-take-all).**
- For winner-take-all with a small field, the strategy that matters is **maximizing probability of finishing 1st**,
  which favors a high-expected-points bracket plus differentiation from the strongest rivals (not wild long shots).
- Entries were due before the first match. Knockout predictions for late entrants are being collected during the
  group stage by organizer's allowance. **Games a participant never predicted score 0** (organizer's ruling).

---

## 2. Participants (use these nicknames everywhere)

| Nickname | Full name | Bracket status | Predicted champion |
|----------|-----------|----------------|--------------------|
| **LF** | Luis Felipe Segura (owner) | Complete | España |
| **Moris** | Mauricio Rubio | Complete | Francia |
| **Rori** | Rodrigo Villa | Complete (final file) | Argentina |
| **Angelou** | Angel Bernal | Complete | España |
| **Luigi** | Luis Giorgana | Complete | Portugal |
| **Toño** | Antonio Hidalgo | **Partial** — texted picks only (matches 1–8 and 13); rest blank = 0 | TBD (full file pending) |

Notes: LF and Angelou share Spain as champion. Distinct champions across complete entries: España (LF, Angelou),
Francia (Moris), Portugal (Luigi), Argentina (Rori).

---

## 3. Scoring rubric (from the workbook "Normas" tab)

Per match: **+2** correct result sign (1/X/2) · **+1** for each exactly correct goal count (home and away
counted separately) · **+2** exact score. Same 2:1:2 ratio every round, weights scale up:
- Group stage: sign 2 / goal 1 / exact 2
- R32 (Dieciseisavos), R16 (Octavos), QF (Cuartos): sign 4 / goal 2 / exact 4
- Semifinals: sign 8 / goal 4 / exact 8
- Final + 3rd-place: sign 16 / goal 8 / exact 16

Progression **bonuses** (dominate the total): correct group winner **+6**; team reaching R32 **+4**, R16 **+4**,
QF **+6**, SF **+8**, finalist **+10**; **champion +25**.

Group-stage-only scoring (used while knockouts are pending) = the 72 group match points + group-winner bonus (+6)
+ R32-qualifier bonus (+4, computed once all 72 group games are in: top 2 per group + 8 best third-placed teams).

---

## 4. Tournament structure / fixtures

- 72 group matches (mid 1–72). Knockouts: R32 (mid 73–88), R16 (89–96), QF (97–100), SF (101–102),
  Final (104) and 3rd-place (103).
- The Excel workbook resolves the bracket automatically from predicted scores, including the FIFA
  best-8-of-12 third-placed allocation. Bracket wiring lives in the workbook's **Aux** sheet (R32 slot codes like
  "2A"/"1E"; thirds via the **Terceros** table; later rounds reference prior match numbers).
- Match-played results so far (recorded): m1 México 2-0 Sudáfrica · m2 Corea 2-1 Rep. Checa ·
  m3 Canadá 1-1 Bosnia · m4 USA 3-1 Paraguay. (More may have been added by the scheduled task — check the data.)
- **Standings after the first 4 games** (group match points): Moris 15 · Toño 12 · LF 11 · Angelou 11 · Rori 10 · Luigi 6.

---

## 5. Files in this project

All paths are under the OneDrive folder:
`/Users/lfsegura/Library/CloudStorage/OneDrive-IncodeTechnologies,Inc/Documents/Claude/Projects/`

- **`Quiniela 2026 - Seguimiento Fase de Grupos.html`** — the main interactive tracker (group stage).
  Group view + date view toggle, per-group standings, a knockout view, leaderboard. Editable (organizer enters
  results). Styled to Incode brand. A scheduled task updates it twice daily.
- **`quiniela-web/index.html`** — read-only copy of the tracker for sharing (score boxes render as plain numbers,
  no editing). For a quick Netlify Drop deploy.
- **`quiniela-github/`** — the auto-updating public site bundle (THIS folder):
  - `index.html` — read-only tracker that overlays `results.json` on load and self-refreshes every 30 min.
  - `results.json` — `{ "<mid>": [homeGoals, awayGoals], ... }` actual results; rewritten by the Action.
  - `scripts/fetch_results.py` — pulls FINISHED World Cup group matches from football-data.org and writes results.json.
  - `scripts/fixtures.json` — `{fixtures:{mid:[homeES,awayES]}, alias:{teamES:[english aliases]}}` for name matching.
  - `.github/workflows/update.yml` — cron (every 2h) + manual; runs the fetcher and commits.
  - `setup_github.sh` — one-shot: creates the repo, pushes, sets the API secret, enables Pages, prints the URL.
  - `README.md` — setup steps.
- **`Quiniela Mundial 2026 - Pronostico LF (winner-take-all).xlsx`** — LF's delivered bracket (the version to submit).
- Each participant's source `.xlsx` lives in the chat uploads (ephemeral); re-request if needed.

### Tracker data schema (inside the single `const DATA = {...};` line)
- `fixtures`: `[{mid, group, home, away, dt(UTC ISO), daykey, daylabel, hm}]`
- `preds`: `{ participant: { "<mid>": [home,away] | [null,null] } }` (null = no prediction → 0 points)
- `predGW`: `{ participant: { group: predictedWinnerTeam } }`
- `actual`: `{ "<mid>": [home,away] }` (results entered/known)
- `entries`: list of participant nicknames

---

## 6. Conventions — DO NOT BREAK

1. **Keep `const DATA = {...};` on a single line.** A scheduled task finds and rewrites that exact line to push
   new results. If you split it across lines or move the data to a separate file, the auto-updater breaks
   (or update the scheduled task accordingly). Use `ensure_ascii=False` when re-dumping so accents stay literal.
2. **Never change anyone's `preds` or `predGW`** (predictions are locked). Only `actual` / `results.json` change.
3. **Incode brand** (apply to all visuals):
   - Palette: black `#000000`, white `#FFFFFF`, off-white `#FAFAFA`, **blue `#006AFF` as a ~5% accent only**,
     mist gray `#EDEDED` (dividers), grays `#232323` / `#666666` / `#CCCCCC`.
     Functional (data only): green `#34A853`, amber `#F5A623`, red `#EA4335`, purple `#7B61FF`.
   - Type: **Rethink Sans** (titles, big numbers) + **DM Sans** (body), both via Google Fonts.
   - Left-aligned, generous whitespace, blue used sparingly. The brand reference is the `incode-brand-pptx` skill.
   - The tracker CSS uses variables `--g50..--g600`, `--b100..--b600`, `--gr*` (green), `--y*` (amber). Re-theme by
     remapping these, not by hardcoding colors.

---

## 7. How the pieces update

- **Scheduled task** (Cowork, runs on LF's machine twice daily): web-searches results, rewrites the tracker's
  `DATA.actual`, recomputes standings, messages LF. Group-stage only for now.
- **Public site** (`quiniela-github`): a GitHub Action runs every 2h, fetches results via football-data.org,
  rewrites `results.json`; the page reads it on load. Truly hands-off once deployed.
- The Cowork sandbox that built this has **no internet** — it cannot create repos, deploy, or post to chat apps.
  All networked actions (GitHub, hosting, messaging) must run from LF's Mac (you, Claude Code) or in GitHub Actions.

---

## 8. Open tasks / how to help

- **Publish the public page:** run `setup_github.sh` (needs `gh` CLI authenticated + a free football-data.org token).
  Then share the `https://<user>.github.io/<repo>/` URL on WhatsApp.
- **Verify live-score matching on first Action run:** football-data.org may spell teams differently
  (e.g., Türkiye, Czechia, Korea Republic, Côte d'Ivoire). If a team doesn't match, add the variant to the alias
  list in `scripts/fixtures.json` (and it flows to the fetcher). Group-stage matching is by team pair.
- **Extend auto-fetch to knockouts** once they start (map by date + teams; bracket teams are dynamic).
- **When Toño's full file arrives:** add his predictions to the tracker `preds`/`predGW`, then run the
  full-tournament Monte Carlo (see below) across all six on equal footing.
- **Keep visuals on Incode brand** (section 6).

### Recompute / analysis notes
- The workbook is self-calculating: enter predicted scores in group sheets A–L, rows [10,12,14,16,18,20],
  column **J** (home) and **L** (away); knockout sheets have score rows with a penalties row beneath each match.
  Recalculate with LibreOffice headless using a profile that forces recalc (OOXMLRecalcMode=0) to resolve the bracket.
- LF's bracket was built scientifically: BetMGM championship odds → team strength ratings → Poisson + Dixon-Coles
  scoreline model → pick the expected-points-maximizing scoreline per the rubric → bracket resolved by the workbook.
  Posture: balanced (favorites base + calculated coin-flip differentiators: Turkey wins Group D, Colombia wins
  Group K; champion Spain). A Monte Carlo (simulate the tournament thousands of times under the model, score each
  entry per the full rubric, count 1st-place finishes) estimates each participant's win probability.

---

## 9. Quick facts to avoid re-deriving

- Group input cells per group sheet (A–L): rows 10,12,14,16,18,20; home goals col J, away goals col L.
- Champion cell after recalc: `Finales!H24`. Group winner: each group sheet `T10`.
- Pre-existing harmless `#VALUE!` cells exist in the workbook's `Equipos` (flag images) and `Terceros` (helper
  column E) tabs — not errors we introduced; ignore them.
- openpyxl strips embedded images on save; to preserve the workbook's flags, inject values via direct XML editing
  of the sheet cells rather than openpyxl save.
