from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from katarina.validation.engine import ValidationDisposition, ValidationResult


class AssetClass(str, Enum):
    FOREX="FOREX"
    METAL="METAL"
    ENERGY="ENERGY"
    INDEX="INDEX"
    CRYPTO="CRYPTO"
    EQUITY="EQUITY"
    OTHER="OTHER"


@dataclass(frozen=True, slots=True)
class TradableInstrument:
    instrument_id: int
    spec_revision: int
    canonical_symbol: str
    broker_symbol: str
    base_currency: str
    profit_currency: str
    margin_currency: str
    asset_class: AssetClass
    trade_allowed: bool
    session_open: bool
    fresh_tick: bool
    terminal_connected: bool
    terminal_trade_allowed: bool
    symbol_trade_allowed: bool

    @property
    def ready(self) -> bool:
        return (
            self.trade_allowed
            and self.session_open
            and self.fresh_tick
            and self.terminal_connected
            and self.terminal_trade_allowed
            and self.symbol_trade_allowed
        )


class MarketTaxonomy:
    @staticmethod
    def infer(symbol:str,base:str="",profit:str="")->AssetClass:
        s=(symbol or "").upper()
        b=(base or "").upper()
        p=(profit or "").upper()
        metals=("XAU","GOLD","XAG","SILVER","XPT","PLAT","XPD","PALL")
        energy=("OIL","WTI","BRENT","UKOIL","USOIL","NGAS","NATGAS")
        crypto=("BTC","ETH","SOL","XRP","ADA","DOGE","LTC","BNB")
        indices=("US30","DJ30","NAS","USTEC","NDX","SPX","US500","GER40","DE40","UK100","JP225","HK50","AUS200","FRA40","EU50")
        if any(x in s or b==x for x in metals): return AssetClass.METAL
        if any(x in s or b==x for x in energy): return AssetClass.ENERGY
        if any(x in s or b==x for x in crypto): return AssetClass.CRYPTO
        if any(x in s for x in indices): return AssetClass.INDEX
        fiat={"USD","EUR","GBP","JPY","CHF","CAD","AUD","NZD","SGD","HKD","CNH","CNY","MXN","ZAR","TRY","NOK","SEK","PLN"}
        if b in fiat and p in fiat: return AssetClass.FOREX
        return AssetClass.OTHER


class SymbolNewsExposureResolver:
    @staticmethod
    def exposures(instrument:TradableInstrument)->tuple[str,...]:
        s=instrument.canonical_symbol.upper()
        tags={instrument.asset_class.value}
        for x in (instrument.base_currency,instrument.profit_currency,instrument.margin_currency):
            if x: tags.add(x.upper())
        if instrument.asset_class is AssetClass.METAL:
            tags.update({"METALS","PRECIOUS_METALS"})
            if "XAU" in s or "GOLD" in s: tags.add("GOLD")
            if "XAG" in s or "SILVER" in s: tags.add("SILVER")
        elif instrument.asset_class is AssetClass.ENERGY:
            tags.update({"ENERGY","OIL"})
        elif instrument.asset_class is AssetClass.CRYPTO:
            tags.add("CRYPTO")
            for token in ("BTC","ETH","SOL","XRP","ADA","DOGE","LTC","BNB"):
                if token in s: tags.add(token)
        elif instrument.asset_class is AssetClass.INDEX:
            tags.update({"EQUITIES","RISK_SENTIMENT","INDEX"})
        elif instrument.asset_class is AssetClass.FOREX:
            tags.add("FX")
        return tuple(sorted(tags))


class BrokerMarketUniverse:
    """Builds the tradable universe from ACCEPTED KAT1 symbol/session state."""

    def __init__(self):
        self._specs:dict[int,dict[str,Any]]={}
        self._sessions:dict[int,dict[str,bool]]={}

    def observe(self,result:ValidationResult)->bool:
        if result.disposition is not ValidationDisposition.ACCEPT:
            return False
        event=result.event
        payload=event.payload
        if not isinstance(payload,Mapping):
            return False

        if event.topic=="symbol.spec":
            instrument_id=int(payload.get("instrument_id",0))
            if instrument_id<=0:return False
            canonical=str(payload.get("canonical_symbol",""))
            broker=str(payload.get("broker_symbol",""))
            base=str(payload.get("base_currency",""))
            profit=str(payload.get("profit_currency",""))
            margin=str(payload.get("margin_currency",""))
            trade_mode=int(payload.get("trade_mode_raw",0))
            self._specs[instrument_id]={
                "instrument_id":instrument_id,
                "spec_revision":int(payload.get("spec_revision",0)),
                "canonical_symbol":canonical or broker,
                "broker_symbol":broker or canonical,
                "base_currency":base,
                "profit_currency":profit,
                "margin_currency":margin,
                "asset_class":MarketTaxonomy.infer(canonical or broker,base,profit),
                "trade_allowed":trade_mode in (1,2,4),
            }
            return True

        if event.topic=="session.state":
            instrument_id=int(payload.get("instrument_id",0))
            if instrument_id<=0:return False
            self._sessions[instrument_id]={
                "session_open":bool(payload.get("session_open",0)),
                "fresh_tick":bool(payload.get("fresh_tick",0)),
                "terminal_connected":bool(payload.get("terminal_connected",0)),
                "terminal_trade_allowed":bool(payload.get("terminal_trade_allowed",0)),
                "symbol_trade_allowed":bool(payload.get("symbol_trade_allowed",0)),
            }
            return True
        return False

    def instruments(self,*,ready_only:bool=True)->tuple[TradableInstrument,...]:
        out=[]
        for iid,s in self._specs.items():
            sess=self._sessions.get(iid,{})
            item=TradableInstrument(
                instrument_id=iid,
                spec_revision=s["spec_revision"],
                canonical_symbol=s["canonical_symbol"],
                broker_symbol=s["broker_symbol"],
                base_currency=s["base_currency"],
                profit_currency=s["profit_currency"],
                margin_currency=s["margin_currency"],
                asset_class=s["asset_class"],
                trade_allowed=bool(s["trade_allowed"]),
                session_open=bool(sess.get("session_open",False)),
                fresh_tick=bool(sess.get("fresh_tick",False)),
                terminal_connected=bool(sess.get("terminal_connected",False)),
                terminal_trade_allowed=bool(sess.get("terminal_trade_allowed",False)),
                symbol_trade_allowed=bool(sess.get("symbol_trade_allowed",False)),
            )
            if not ready_only or item.ready:
                out.append(item)
        return tuple(sorted(out,key=lambda x:x.canonical_symbol))
