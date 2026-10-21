# Claude ↔ OpenAI API Connector

A standalone, authenticated remote MCP server for Claude Web and Mobile.

**This connects Claude to a separate OpenAI API model, not to this ChatGPT account, chat history, memory or the assistant's direct tool sessions.** It does not give Claude control of the Katarina VPS. The existing Desktop Commander connector handles VPS access separately.

## MCP endpoint

`https://<your-service>.onrender.com/mcp`

## Authentication

Configure Claude Custom Web Connector using **Authentication: No sign in**, and under **Request headers** add:

- Header name: `X-Connector-Key`
- Header value: the private generated `CONNECTOR_KEY` that also exists as a Render environment variable.

Never commit keys to GitHub or put them in Claude chat messages.

## Server environment variables

- `CONNECTOR_KEY` **required**: cryptographically random 32 bytes encoded as 64 hexadecimal chars.
- `OPENAI_API_KEY` **required to use ask_openai**: set privately in Render Environment (secret).
- `OPENAI_MODEL` optional, defaults to `gpt-5-mini`.
- `PORT` Render injects automatically.

The server fails closed without CONNECTOR_KEY. If OPENAI_API_KEY has not been set, `connector_status` works but `ask_openai` returns `OPENAI_API_KEY_NOT_CONFIGURED`. API usage may incur separate charges.

## MCP tools

- `connector_status`: reports service and OpenAI-key readiness without calling the API.
- `ask_openai`: takes question and optional context, sends them to OpenAI Responses API. Does not use ChatGPT saved memories.

Request headers are required for MCP tool calls. Store no chat context server-side; `store:false` is requested on the OpenAI response API.

## Security

- No shell execution or file access.
- Max 2 simultaneous API requests, 8 requests/minute per service instance.
- Input bounded; 65 sec API request timeout; no question or API key in logs.
- Do not send broker credentials, SSH keys, or proprietary files unless explicitly authorized.
- This folder is isolated under `claude-vps-bridge`; GitHub main and Windows VPS files remain untouched.
