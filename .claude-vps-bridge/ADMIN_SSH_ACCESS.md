# Claude Web & Mobile — Windows VPS access

**Current supported path: Remote Desktop Commander (Remote MCP with OAuth).**
For Claude used through https://claude.ai or the Claude mobile app, do **not**
try to upload an SSH private key into a conversation or GitHub repository.

## Add the connector in Claude

1. In Claude Web, open **Customize → Connectors → Add → Custom → Web**.
2. Connector name: `Katarina VPS — Desktop Commander`
3. MCP URL: `https://mcp.desktopcommander.app/mcp`
4. Complete OAuth sign-in with the **Desktop Commander Dc 2 account** paired
   to the VPS (not a generic GitHub account).
5. Enable the connector in the Claude chat using **+ → Connectors**.
6. Ask Claude to list connected devices, choose `WIN-4TTT19K3CL8`, and
   first run harmless checks such as `whoami` and disk space.

Remote Desktop Commander is already paired with the Windows VPS via Dc 2.
Full file/terminal access inherits the permissions of its local agent, which
has been observed as Administrator in this deployment. Do not change the
Desktop Commander connection or Windows RDP/SSH/network configuration.

## Important

- The experiment to use an extra self-hosted localhost MCP gateway was
  removed because the existing Desktop Commander Remote MCP supports
  Claude Web and Mobile directly.
- The previously created dedicated Claude SSH administrator key was revoked
  and deleted when direct SSH was found unnecessary for Claude Web/Mobile.
- The limited GitHub message transport remains separate in
  `.claude-vps-bridge/`; **never** submit privileged commands or secrets to
  that public GitHub repository.
- Claude-to-VPS connectivity is **not complete** until the user authorizes
  Desktop Commander in Claude and runs a verification command there.
- Trading LIVE is NOT authorized by the existence of this connector.
- References: https://desktopcommander.app/ and
  https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp .
