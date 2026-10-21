"""Prune only GitHub branches proven redundant with main. Fail closed.

A branch is eligible when it is a strict ancestor of main, or when it is listed
in the committed superseded-branch registry and still points at exactly the
recorded commit (content already reviewed as present in main or intentionally
removed). Protected branches, main, and branches used by open PRs are never
eligible.
"""
import argparse
import json
import os
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_REGISTRY = "docs/maintenance/superseded-branches.json"


def eligible(branch, comparison, open_heads, superseded=None):
    name = branch.get("name", "")
    if not name or name == "main" or branch.get("protected") is not False:
        return False
    if name in open_heads:
        return False
    if (comparison.get("ahead_by") == 0
            and comparison.get("behind_by", 0) > 0
            and comparison.get("status") == "behind"):
        return True
    recorded = (superseded or {}).get(name)
    sha = (branch.get("commit") or {}).get("sha")
    return bool(recorded) and bool(sha) and sha == recorded


def load_superseded(path):
    """Read {branch: full 40-hex sha}; reject anything else."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("branches") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValueError("superseded_registry_invalid")
    result = {}
    for row in rows:
        name, sha = row.get("name"), row.get("sha")
        if (not isinstance(name, str) or not name or name == "main"
                or not isinstance(sha, str) or len(sha) != 40
                or any(c not in "0123456789abcdef" for c in sha)):
            raise ValueError("superseded_registry_invalid")
        result[name] = sha
    return result


def collection(api, path):
    """Read a complete snapshot before any deletion changes pagination."""
    result = []
    for page in range(1, 21):
        rows = api(f"{path}&per_page=100&page={page}")
        result.extend(rows)
        if len(rows) < 100:
            return result
    raise RuntimeError("pagination_limit_reached_cleanup_blocked")


def active_pr_branches(api, repo):
    refs = set()
    for pr in collection(api, "/pulls?state=open"):
        for side in ("head", "base"):
            branch = pr.get(side) or {}
            if (branch.get("repo") or {}).get("full_name") == repo:
                refs.add(branch["ref"])
    return refs


def cleanup(api, repo, *, execute=False, max_deletes=10, superseded=None):
    if not 1 <= max_deletes <= 10:
        raise ValueError("max_deletes_must_be_between_1_and_10")
    open_refs = active_pr_branches(api, repo)
    branches = collection(api, "/branches?")
    report = {"dry_run": not execute, "candidates": [], "deleted": [],
              "max_deletes": max_deletes}
    for branch in branches:
        name = branch["name"]
        if name == "main":
            continue
        encoded = quote(name, safe="")
        comparison = api("/compare/main..." + encoded)
        if not eligible(branch, comparison, open_refs, superseded):
            continue
        report["candidates"].append(name)
        if not execute or len(report["deleted"]) >= max_deletes:
            continue
        fresh = api("/branches/" + encoded)
        fresh_compare = api("/compare/main..." + encoded)
        # PRs may be opened while the run is in progress. Protect both ends.
        fresh_refs = active_pr_branches(api, repo)
        if (fresh["commit"]["sha"] != branch["commit"]["sha"]
                or not eligible(fresh, fresh_compare, fresh_refs, superseded)):
            continue
        api("/git/refs/heads/" + quote(name, safe="/"), "DELETE")
        report["deleted"].append(name)
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true")
    p.add_argument("--max-deletes", type=int, default=10)
    p.add_argument("--superseded", default=DEFAULT_REGISTRY)
    args = p.parse_args()
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    def api(path, method="GET"):
        request = Request("https://api.github.com/repos/" + repo + path, method=method,
                          headers={"Authorization": "Bearer " + token,
                                   "Accept": "application/vnd.github+json",
                                   "User-Agent": "katarina-guarded-cleanup"})
        with urlopen(request, timeout=25) as response:
            return json.load(response) if method == "GET" else response.status

    report = cleanup(api, repo, execute=args.execute, max_deletes=args.max_deletes,
                     superseded=load_superseded(args.superseded))
    os.makedirs("build/validation", exist_ok=True)
    with open("build/validation/branch-cleanup.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("PASS_GUARDED_BRANCH_CLEANUP", json.dumps(report))


if __name__ == "__main__":
    main()
