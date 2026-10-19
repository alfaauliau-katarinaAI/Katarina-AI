"""Explicit JSON chat adapter. No discovery, automatic model choice or tool execution."""
from dataclasses import dataclass
import ipaddress
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler


class ModelUnavailable(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ModelUnavailable('MODEL_REDIRECT_REJECTED')


@dataclass(frozen=True)
class ModelConfig:
    endpoint: str
    fast_model: str
    deep_model: str
    token_env: str = 'KATARINA_MODEL_TOKEN'
    timeout_seconds: int = 30
    max_output_tokens: int = 800
    api_format: str = 'chat_completions'

    def __post_init__(self):
        try:
            if self.api_format not in ('chat_completions', 'responses'):
                raise ValueError()
            p = urlsplit(self.endpoint)
            loopback = p.hostname == 'localhost'
            if p.hostname and not loopback:
                try:
                    loopback = ipaddress.ip_address(p.hostname).is_loopback
                except ValueError:
                    pass
            if (not p.hostname or p.username or p.password or p.query or p.fragment
                    or p.port == 0 or (p.scheme != 'https' and not (p.scheme == 'http' and loopback))):
                raise ValueError()
            if (not all(isinstance(x, str) and 0 < len(x) <= 160 for x in
                        (self.fast_model, self.deep_model))
                    or not isinstance(self.token_env, str) or not self.token_env.isidentifier()
                    or type(self.timeout_seconds) is not int or not 1 <= self.timeout_seconds <= 60
                    or type(self.max_output_tokens) is not int or not 64 <= self.max_output_tokens <= 4096):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ValueError('invalid_model_config') from None

    @classmethod
    def load(cls, path):
        try:
            return cls(**json.loads(Path(path).read_text(encoding='utf-8')))
        except (OSError, ValueError, TypeError):
            raise ValueError('invalid_model_config') from None


class JSONDialogModel:
    """User-configured chat-completions JSON protocol; credentials never enter memory."""
    def __init__(self, config, *, exchange=None):
        self.config = config
        self.exchange = exchange or self._http
        self._telemetry = dict(successful_calls=0, failed_calls=0, last_duration_ms=None,
                               transport='LIVE_HTTP' if exchange is None else 'INJECTED_TEST_EXCHANGE',
                               fast_model=config.fast_model, deep_model=config.deep_model)

    def telemetry(self):
        return dict(self._telemetry)

    def _http(self, payload):
        token = os.environ.get(self.config.token_env, '')
        if urlsplit(self.config.endpoint).scheme == 'https' and not token:
            raise ModelUnavailable('MODEL_CREDENTIAL_REQUIRED')
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = Request(self.config.endpoint, data=json.dumps(payload, allow_nan=False).encode(),
                      headers=headers, method='POST')
        try:
            with build_opener(ProxyHandler({}), NoRedirect()).open(
                    req, timeout=self.config.timeout_seconds) as response:
                raw = response.read(131073)
            if len(raw) > 131072:
                raise ValueError()
            return json.loads(raw)
        except Exception:
            raise ModelUnavailable('MODEL_REQUEST_FAILED') from None

    def complete(self, messages, *, mode):
        if mode not in ('fast', 'deep'):
            raise ValueError('invalid_model_mode')
        payload = {'model': self.config.deep_model if mode == 'deep' else self.config.fast_model,
                   'messages': messages, 'max_tokens': self.config.max_output_tokens,
                   'response_format': {'type': 'json_object'}}
        if self.config.api_format == 'responses':
            payload = dict(model=payload['model'], input=messages,
                           max_output_tokens=self.config.max_output_tokens, store=False,
                           text={'format': {'type': 'json_object'}},
                           reasoning={'effort': 'medium' if mode == 'deep' else 'low'})
        if len(json.dumps(payload, allow_nan=False)) > 100000:
            raise ModelUnavailable('MODEL_CONTEXT_TOO_LARGE')
        started = time.monotonic()
        try:
            response = self.exchange(payload)
            if self.config.api_format == 'responses':
                if response.get('status') != 'completed':
                    raise ValueError()
                chunks = [part['text'] for item in response.get('output', [])
                          if isinstance(item, dict) and item.get('type') == 'message'
                          for part in item.get('content', [])
                          if isinstance(part, dict) and part.get('type') == 'output_text']
                raw = ''.join(chunks)
            else:
                raw = response['choices'][0]['message']['content']
            if not isinstance(raw, str) or len(raw) > 16000:
                raise ValueError()
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError()
            self._telemetry['successful_calls'] += 1
            return result
        except ModelUnavailable:
            self._telemetry['failed_calls'] += 1
            raise
        except Exception:
            self._telemetry['failed_calls'] += 1
            raise ModelUnavailable('MODEL_RESPONSE_INVALID') from None
        finally:
            self._telemetry['last_duration_ms'] = round((time.monotonic()-started)*1000)
