"""Small private Hub round trip; accepts credentials only through HF_TOKEN."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import urllib.error
import urllib.request


def main():
    phase = "secret"
    started = time.monotonic()
    try:
        token = os.environ.get("HF_TOKEN", "").strip()
        if not token:
            raise ValueError("HF_TOKEN_MISSING")
        from huggingface_hub import HfApi, hf_hub_download

        phase = "authentication"
        api = HfApi(token=token)
        identity = api.whoami()
        if identity.get("name") != "alfaaulia":
            raise ValueError("UNEXPECTED_HF_ACCOUNT")
        print("HF_TOKEN_PRESENT; AUTHENTICATION_OK; ACCOUNT=alfaaulia", flush=True)
        phase = "private_repository"
        repo = "alfaaulia/katarina-storage-smoke-test"
        api.create_repo(repo_id=repo, repo_type="dataset", private=True, exist_ok=True)
        if api.repo_info(repo_id=repo, repo_type="dataset").private is not True:
            raise ValueError("REPOSITORY_NOT_PRIVATE")
        # Generated fixtures only: never read trading, account, or VPS data.
        payload = ("\n".join(json.dumps({"synthetic": True, "worker": f"W{i:02d}",
                   "test": "storage-round-trip", "value": i}) for i in range(1, 13)) + "\n").encode()
        expected = hashlib.sha256(payload).hexdigest()
        phase = "upload"
        commit = api.upload_file(path_or_fileobj=payload, path_in_repo="smoke/synthetic.jsonl",
                                 repo_id=repo, repo_type="dataset",
                                 commit_message="Verify synthetic Katarina storage fixture")
        phase = "download_checksum"
        with tempfile.TemporaryDirectory(prefix="katarina-hf-smoke-") as cache:
            downloaded = hf_hub_download(repo_id=repo, repo_type="dataset",
                         filename="smoke/synthetic.jsonl", revision=commit.oid,
                         token=token, cache_dir=cache, force_download=True)
            restored = Path(downloaded).read_bytes()
            if restored != payload or hashlib.sha256(restored).hexdigest() != expected:
                raise ValueError("CHECKSUM_MISMATCH")
        phase = "anonymous_access"
        url = f"https://huggingface.co/datasets/{repo}/resolve/{commit.oid}/smoke/synthetic.jsonl"
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                response.read(4096)
            raise ValueError("ANONYMOUS_ACCESS_ALLOWED")
        except urllib.error.HTTPError as error:
            if error.code not in (401, 403, 404):
                raise ValueError("ANONYMOUS_CHECK_INCONCLUSIVE") from None
        report = {"status": "PASS", "repo": repo, "private": True,
                  "bytes": len(payload), "sha256": expected, "revision": commit.oid,
                  "authenticated": True, "uploaded": True, "download_verified": True,
                  "anonymous_access_denied": True,
                  "seconds": round(time.monotonic() - started, 3), "synthetic_only": True}
        print(json.dumps(report), flush=True)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
                summary.write("### Hugging Face private storage smoke test\n\n```json\n" +
                              json.dumps(report, indent=2) + "\n```\n")
        return 0
    except Exception as error:
        # Never log exception bodies, request headers, identities, or tokens.
        status = getattr(getattr(error, "response", None), "status_code", None)
        known = {"HF_TOKEN_MISSING", "UNEXPECTED_HF_ACCOUNT", "REPOSITORY_NOT_PRIVATE",
                 "CHECKSUM_MISMATCH", "ANONYMOUS_ACCESS_ALLOWED", "ANONYMOUS_CHECK_INCONCLUSIVE"}
        reason = str(error) if isinstance(error, ValueError) and str(error) in known else type(error).__name__
        print(json.dumps({"status": "FAIL", "phase": phase, "reason": reason,
                          "http_status": status}), flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
