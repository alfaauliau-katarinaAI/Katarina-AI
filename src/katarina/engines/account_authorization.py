"""Account identity comes exclusively from the installed MT5 SDK."""
from dataclasses import dataclass
from math import isfinite


def account_mode(broker, account):
    value = getattr(account, 'trade_mode', None)
    if type(value) is not int:
        return 'UNKNOWN'
    matches = [name for name in ('DEMO', 'REAL', 'CONTEST')
               if type(getattr(broker, 'ACCOUNT_TRADE_MODE_'+name, None)) is int
               and getattr(broker, 'ACCOUNT_TRADE_MODE_'+name) == value]
    return matches[0] if len(matches) == 1 else 'UNKNOWN'


def account_key(broker, account):
    mode = account_mode(broker, account)
    login, server = getattr(account, 'login', None), getattr(account, 'server', None)
    if mode == 'UNKNOWN' or type(login) is not int or login <= 0 or not isinstance(server, str) or not server:
        raise ValueError('ACCOUNT_IDENTITY_UNVERIFIED')
    return mode, login, server


@dataclass(frozen=True)
class AccountAuthorization:
    mode: str
    login: int
    server: str
    strategies: frozenset[str]
    max_risk_fraction: float
    max_margin_fraction: float
    expires_at: float

    def __post_init__(self):
        if (self.mode not in ('DEMO', 'REAL', 'CONTEST') or type(self.login) is not int
                or self.login <= 0 or not isinstance(self.server, str) or not self.server
                or not isinstance(self.strategies, frozenset) or not self.strategies
                or any(not isinstance(s, str) or len(s) != 64 or any(c not in '0123456789abcdef' for c in s) for s in self.strategies)
                or any(type(v) not in (float, int) or not isfinite(v) or not 0 < v <= 1
                       for v in (self.max_risk_fraction, self.max_margin_fraction))
                or type(self.expires_at) not in (float, int) or not isfinite(self.expires_at) or self.expires_at <= 0):
            raise ValueError('INVALID_ACCOUNT_AUTHORIZATION')

    @property
    def key(self):
        return self.mode, self.login, self.server

    @classmethod
    def from_dict(cls, data):
        return cls(**{**data, 'strategies': frozenset(data['strategies'])})
