'use strict';

const http = require('http');
const { URL, URLSearchParams } = require('url');
const crypto = require('crypto');

const PORT = Number(process.env.PORT || 10000);
const HOST = process.env.HOST || '127.0.0.1'; // Default loopback binding. WARNING: Binding externally exposes gateway.
const CLIENT_ID = process.env.MQL5_CLIENT_ID || '';
const CLIENT_SECRET = process.env.MQL5_CLIENT_SECRET || '';
const BASE_URL = (process.env.APP_BASE_URL || '').replace(/\/$/, '');

const AUTH_URL = 'https://www.mql5.com/en/oauth/login';
const TOKEN_URL = 'https://www.mql5.com/api/oauth/access_token';
const USER_URL = 'https://www.mql5.com/api/oauth/user_info';

const states = new Map();
let lastAuth = { ok: false, at: null, error: null };

function sendJson(res, status, body) {
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff',
  });
  res.end(JSON.stringify(body, null, 2));
}

function sendHtml(res, status, html) {
  res.writeHead(status, {
    'content-type': 'text/html; charset=utf-8',
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff',
    'content-security-policy': "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'",
  });
  res.end(html);
}

async function postForm(url, params, bearer) {
  const headers = { 'content-type': 'application/x-www-form-urlencoded' };
  if (bearer) headers.authorization = 'Bearer ' + bearer;
  const resp = await fetch(url, {
    method: 'POST',
    headers,
    body: new URLSearchParams(params).toString(),
    redirect: 'manual',
  });
  const text = await resp.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { raw: text.slice(0, 1000) }; }
  return { status: resp.status, ok: resp.ok, data };
}

async function fetchUserInfo(accessToken) {
  const attempts = [
    () => postForm(USER_URL, { client_id: CLIENT_ID }, accessToken),
    () => postForm(USER_URL, { client_id: CLIENT_ID, access_token: accessToken }),
    () => postForm(USER_URL, { client_id: CLIENT_ID, token: accessToken }),
  ];
  let last;
  for (const attempt of attempts) {
    last = await attempt();
    if (last.ok && !last.data?.error) return last;
  }
  return last;
}

function callbackUrl() {
  return BASE_URL ? BASE_URL + '/oauth/callback' : '';
}

const server = http.createServer(async (req, res) => {
  try {
    const base = BASE_URL || 'http://localhost:' + PORT;
    const url = new URL(req.url, base);

    if (url.pathname === '/health') {
      return sendJson(res, 200, {
        ok: true,
        service: 'katarina-mql5-oauth-gateway',
        oauthConfigured: Boolean(CLIENT_ID && CLIENT_SECRET && BASE_URL),
        callbackUrl: callbackUrl() || null,
      });
    }

    if (url.pathname === '/') {
      return sendHtml(res, 200, `<!doctype html><meta charset="utf-8">
<title>Katarina MQL5 OAuth Gateway</title>
<style>body{font-family:system-ui;max-width:760px;margin:50px auto;padding:20px;line-height:1.5}code{background:#eee;padding:2px 5px}.ok{color:green}.bad{color:#a00}</style>
<h1>Katarina MQL5 OAuth Gateway</h1>
<p>Gateway status: <b class="${CLIENT_ID && CLIENT_SECRET && BASE_URL ? 'ok' : 'bad'}">${CLIENT_ID && CLIENT_SECRET && BASE_URL ? 'configured' : 'awaiting MQL5 credentials'}</b></p>
<p><a href="/health">Health</a>${CLIENT_ID && CLIENT_SECRET && BASE_URL ? ' · <a href="/oauth/start">Start MQL5 OAuth</a>' : ''}</p>
<p>This service stores no MQL5 password and does not expose OAuth access tokens.</p>`);
    }

    if (url.pathname === '/oauth/start') {
      if (!CLIENT_ID || !CLIENT_SECRET || !BASE_URL) {
        return sendJson(res, 503, { ok: false, error: 'OAuth environment is not configured yet.' });
      }
      const state = crypto.randomBytes(24).toString('hex');
      states.set(state, Date.now());
      for (const [k, t] of states) if (Date.now() - t > 10 * 60 * 1000) states.delete(k);

      const target = new URL(AUTH_URL);
      target.searchParams.set('client_id', CLIENT_ID);
      target.searchParams.set('redirect_uri', callbackUrl());
      target.searchParams.set('response_type', 'code');
      target.searchParams.set('state', state);
      res.writeHead(302, { location: target.toString(), 'cache-control': 'no-store' });
      return res.end();
    }

    if (url.pathname === '/oauth/callback') {
      const code = url.searchParams.get('code');
      const state = url.searchParams.get('state');
      const oauthError = url.searchParams.get('error');
      if (oauthError) return sendJson(res, 400, { ok: false, error: oauthError });
      if (!code || !state || !states.has(state)) {
        return sendJson(res, 400, { ok: false, error: 'Missing/invalid authorization code or state.' });
      }
      states.delete(state);

      const tokenResp = await postForm(TOKEN_URL, {
        grant_type: 'authorization_code',
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        code,
        redirect_uri: callbackUrl(),
      });
      const accessToken = tokenResp.data?.access_token;
      if (!tokenResp.ok || !accessToken) {
        lastAuth = { ok: false, at: new Date().toISOString(), error: 'Token exchange failed' };
        return sendJson(res, 502, { ok: false, error: 'MQL5 token exchange failed', status: tokenResp.status });
      }

      const userResp = await fetchUserInfo(accessToken);
      if (!userResp?.ok || userResp.data?.error) {
        lastAuth = { ok: false, at: new Date().toISOString(), error: 'user_info failed' };
        return sendJson(res, 502, { ok: false, error: 'MQL5 user_info failed', status: userResp?.status || null });
      }

      lastAuth = {
        ok: true,
        at: new Date().toISOString(),
        error: null,
      };

      return sendHtml(res, 200, '<!doctype html><meta charset="utf-8"><title>MQL5 OAuth OK</title><h1>MQL5 OAuth succeeded</h1><p>Identity endpoint responded successfully. No token is shown or stored persistently.</p>');
    }

    if (url.pathname === '/oauth/status') {
      return sendJson(res, 200, {
        ok: lastAuth.ok,
        at: lastAuth.at,
        error: lastAuth.error,
      });
    }

    return sendJson(res, 404, { ok: false, error: 'Not found' });
  } catch (err) {
    console.error(err);
    return sendJson(res, 500, { ok: false, error: 'Internal server error' });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`Katarina MQL5 OAuth Gateway listening on ${HOST}:${PORT}`);
});
