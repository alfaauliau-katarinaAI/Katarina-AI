# GitHub Actions request and repository queue cleanup — 12 October 2026

## What was measured (not assumed)

GitHub REST snapshots before cleanup:
- 1,088 *historical* workflow runs in the repository.
- **0 QUEUED, 0 IN_PROGRESS, 0 WAITING** at the audit snapshot. Historical
  failed runs cannot legitimately be called current pending requests.
- Last 100 history entries: 77 success, 22 failure, 1 cancelled;
  the 22 failures are **old immutable records**, mostly superseded by
  later green commits. Recent main Body CI, Stage 10-40 and Operational
  Hardening runs succeeded. The previous isolated XAU workflow's
  `open(` static false-positive was fixed and rerun green.
- 31 workflow definitions, including very similar Stage07 and
  one-off V9/V10 research safety checks.
- Two unmerged *draft* PRs, #30 and #32. Do not auto-merge unreviewed
  draft research into the production main.
- 7 open issues in the GitHub issue API, of which 2 are those PRs.

## Changes in the repository

**One canonical push/PR validation path**:
`katarina-body-ci.yml` remains automatic for production code,
configuration, broker integration and workflow file changes. Its
existing concurrency/cancellation guard is retained. Documentation,
`*.md` and frequently rewritten generated
`website/hot-news.json` are exempted from this heavyweight check,
but source/protocol/tests are NOT exempted.

**Targeted special automatic checks preserved:**
- `stage35-tester-safety.yml` still runs when real native tester
  files change. Its formerly unscoped `pull_request` event now
  carries the same paths filter as `push`, rather than running on
  every unrelated draft PR change.
- `katarina-hotnews.yml` keeps the existing scheduled cadence and
  credential scope (six-hour frequency; no new cron). Its generated
  data no longer causes redundant Body CI pushes.

**Other historical workflows:** convert the 26 previously push/PR
triggered research, Stage06, Stage07, Stage08/09, legacy VPS bootstrap
and duplicate Stage10/Operational workflows to
**`workflow_dispatch` on-demand only**. They remain in the
repository for reproducibility and native validation; no dangerous
deletion of MT5 source, hard-governor logic or signed test evidence.
The two self-hosted VPS workflows were already manual-only and
remain that way.

**Proactive regression guard:**
`tests/static/test_github_action_fanout.py` runs inside primary
Body CI. It fails if any other GitHub Action grows automatic
push/PR/schedule/repository/issue hooks, if Body CI loses
cancellation/ignore rules, or if VPS workflows gain automatic triggers.

This reduces default CI fanout. It **does not** delete GitHub's 1,088
historical workflow records. Deleting the immutable CI history
would hide useful failure evidence and is not required to free
the queue or reduce requests.

## Open requests

The two draft PRs contain unmerged research and must **not** be
silently merged. If closed as part of request cleanup, preserve their
branches and clearly state that their code was not promoted. Keep
genuine forward-data/authorization blockers open; close only duplicate
issue trackers with cross-references, not unresolved safety work.

## Important operating rules

- Trigger expensive Windows-native Stage07/Stage06 historical CI
  with `workflow_dispatch` **only when editing that subsystem**.
  Body CI is the gate on routine commits; manual Windows CI remains
  a required specialist validation before shipping changed MQL5
  components. No live broker activity, self-hosted VPS job or auto
  trading may be started by repository pushes.
- If actual GitHub API HTTP 429 or rate-limit failures recur,
  separately inspect client retries, parallelism and the GitHub
  response headers. This audit found excess CI fanout and old runs,
  **not proof of a current GitHub API rate-limit error**.
- Latest job/status verification is required after the cleanup
  commit. Do not claim the CI green until the run finishes.


## Final verified outcome

Cleanup implementation: [commit `1d385ff`](https://github.com/alfaauliau-katarinaAI/Katarina-AI/commit/1d385ff4ee53774900580f15177c6b166a382e6b).

- **26 previously automatic workflows** converted to on-demand only;
  stage-specific Windows/MT5 integration tests remain available
  explicitly via GitHub Actions when that subsystem actually changes.
- **3 retained unattended workflows** out of 31:
  primary `KATARINA Body CI` (source/PR), path-limited Stage 35 native
  tester safety, and six-hour scheduled verified-hotnews backup.
  Two separate self-hosted VPS jobs remain manual-only.
- **2 draft PRs closed unmerged**: [#30](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/30)
  (experimental Brain V3 paper journal) and
  [#32](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/32)
  (experimental multi-asset portfolio). The source branches still
  exist; no experimental trade code was merged under the guise of
  cleanup. Both PRs have explicit archival explanations.
- **1 confirmed duplicate issue closed**: [#27](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/27)
  in favor of more complete [#29](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/29).
  Four genuine open issues (#21/#24/#29/#31) are retained because
  merchant, release and forward broker evidence is still outstanding.
- Final GitHub REST validation: **0 queued, 0 waiting,
  0 in-progress runs; 0 open PRs**.
- Latest relevant workflow runs on commit `1d385ff`:
  [KATARINA Body CI: SUCCESS](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38212804784)
  and [Stage35 Tester Safety: SUCCESS](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38212804762).
- The repository-wide static fanout regression is covered in Body CI;
  no need to erase historical CI failures, rewrite main history or
  delete safety-critical research and MQL5 artifacts.
- This reduces excessive GitHub Actions executions, but **does not
  demonstrate that any independent GitHub API HTTP 429 has been
  fixed**. If an API client itself exceeds request limits it still
  needs separate rate-limit response/retry analysis.
