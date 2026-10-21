# Claude ↔ VPS bridge (isolated)

Transport: GitHub branch `claude-vps-bridge` of this **public** repository, using only `.claude-vps-bridge/`. **Do not post credentials, broker data, account IDs or other private information** here.

## Message protocol v1

An authorized GitHub writer (e.g., Claude through its GitHub integration) submits an immutable UTF-8 JSON file to `.claude-vps-bridge/inbox/<id>.json`. IDs must match `[a-zA-Z0-9_-]{8,64}`; never edit an existing request.

```json
{"version":1,"id":"ping-20261022-001","action":"ping"}
```

The VPS polls the branch by outbound HTTPS (no inbound public port), processes supported **non-executing** operations and writes `.claude-vps-bridge/outbox/<id>.json` with the same ID and a success/error code. Replies contain only safe summary data.

Supported actions:
- `ping`: connectivity check (UTC timestamp).
- `status`: bridge health and available disk space, **not** system secrets.
- `list_workspace`: filenames only within isolated `C:\ClaudeGitHubBridge\workspace`.
- `write_text`: create a new bounded UTF-8 text file within that isolated workspace (no overwrites). Fields: `file` (a simple filename ending `.txt`, `.md`, or `.json`, no path separators), `content` (up to 16 KiB).
- `read_text`: read up to 16 KiB from one isolated workspace file, same filename restrictions. Replies are visible to the public, so do not put sensitive content in this workspace.

No PowerShell/shell execution, arbitrary filesystem access, MT5, registry or services are exposed. The bridge never downloads or runs code from GitHub. GitHub commit permission is required to send requests; **the public may read every message**.

All changes must stay in the branch and the isolated VPS directory. The GitHub main branch, other VPS files, RDP and Desktop Commander are untouched.

Execution only works while the VPS bridge polling task is running and Git credentials allow it to post replies. No claim of a two-way connection until an outbox reply is observed.
