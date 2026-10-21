"""Immutable shadow study manifest, binds journal to one account & setup.

Stops accidental reuse of an existing paper trading journal with different
starting capital, version, broker account or risk policy on restart. This
provides reproducibility and fail-closed local state, not broker attestation.
"""
from __future__ import annotations

from dataclasses import asdict,dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
import json,os


@dataclass(frozen=True,slots=True)
class ShadowStudyIdentity:
    strategy_version: str
    frozen_at_utc: str
    symbol: str
    account_currency: str
    broker_account_fingerprint: str
    initial_paper_balance_native: float
    risk_config_sha256: str
    commission_per_lot_assumed: float | None


def verify_or_create_manifest(directory: str | Path,
                              identity: ShadowStudyIdentity) -> bool:
    root=Path(directory)
    root.mkdir(parents=True,exist_ok=True)
    if (not identity.strategy_version or not identity.frozen_at_utc
        or not identity.symbol or not identity.account_currency
        or len(identity.broker_account_fingerprint)!=64
        or len(identity.risk_config_sha256)!=64
        or not isfinite(identity.initial_paper_balance_native)
        or identity.initial_paper_balance_native<=0):
        raise ValueError("invalid_shadow_study_identity")
    if identity.commission_per_lot_assumed is not None and (
        not isfinite(identity.commission_per_lot_assumed) or
        identity.commission_per_lot_assumed<0):
        raise ValueError("invalid_shadow_study_commission")
    doc=asdict(identity)
    text=json.dumps(doc,sort_keys=True,separators=(",",":"),allow_nan=False)
    path=root/"manifest.json"
    if path.exists():
        try:
            stored=json.loads(path.read_text(encoding="utf-8"))
        except (ValueError,OSError,UnicodeError) as exc:
            raise ValueError("corrupt_study_manifest") from exc
        if stored!=doc:
            raise ValueError("shadow_study_identity_mismatch")
        return False
    content=(text+"\n").encode()
    try:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError as exc:
        raise ValueError("concurrent_manifest_creation") from exc
    with os.fdopen(fd,"wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    return True


def broker_fingerprint(*,server:str, login:object,currency:str)->str:
    if not server or not currency or not isinstance(login,(str,int)) or str(login)=="":
        raise ValueError("unverified_broker_account_identity")
    return sha256((server+"|"+str(login)+"|"+currency).encode()).hexdigest()


def config_sha256(path:str|Path)->str:
    source=Path(path).read_bytes()
    if not source:
        raise ValueError("empty_risk_config")
    return sha256(source).hexdigest()
