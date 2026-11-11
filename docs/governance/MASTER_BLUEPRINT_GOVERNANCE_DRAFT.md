# KATARINA MASTER BLUEPRINT — GOVERNANCE DRAFT

Status: DRAFT — owner approval of governance principles received 2026-10-29; technical baseline not yet frozen.
Authority: Project Owner. Existing KATARINA_CONSTITUTION.md v1.1.0 remains higher authority.

## Source-of-truth hierarchy
1. KATARINA_CONSTITUTION.md (existing FROZEN constitution).
2. Approved and versioned Master Blueprint (requirements, architecture, acceptance criteria).
3. Approved decision records / change requests.
4. ROADMAP.md (execution tracking only).
5. Operational logs and evidence (observed state, not policy).

## Change control
- Major changes to mission, risk, live-trading behavior, architecture contracts, validation criteria, or frozen requirements require explicit owner approval before implementation.
- Minor technical fixes that preserve approved behavior may be made by Yura or Claude, but MUST be logged with work ID, UTC timestamp, author, affected files, reason, test evidence, commit hash (if available), and rollback instructions.
- Never mark an item DONE without acceptance evidence. Use BLOCKED or UNVERIFIED when appropriate.
- Every work item has one owner, one acceptance definition, dependencies, and links to evidence. Avoid duplicate work IDs.
- No silent changes to approved blueprint. Propose changes in a change request and increment version after approval.

## Token-efficient handoff
- Read this governance file, KATARINA_CONSTITUTION.md, current PROJECT_STATUS.md, and only the relevant work-item/decision files before touching code.
- Maintain a concise latest-state summary: active work ID, current status, blocker, last verified commit, next action, and evidence paths.
- Append one compact entry per meaningful minor fix; do not rescan the entire repository unless a dependency or evidence requires it.
- At handoff, cite exact changed files and tests instead of repeating long chat histories.

## Initial application
WP13 broker clock/quote freshness: remains UNVERIFIED until code and four scenario tests (normal session, stale quote, weekend, DST) are checked. Fail closed for unreliable timing; do not derive a new broker offset from stale quotes.

## Approval boundary
This draft records the owner's approval of major/minor change governance. The complete technical blueprint and its baseline version still require review and approval before being labeled FROZEN.
