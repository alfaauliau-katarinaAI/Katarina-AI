"""GitHub-hosted deterministic KATARINA autonomy safety proof.

No MT5 or network dependencies; synthetic quote fixtures ONLY.
This certifies software safety contracts, not market profitability.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))

from katarina.intelligence.shadow.prospective_shadow_book import (
    ProspectiveShadowBook,ResearchHypothesis
)
from katarina.intelligence.shadow.prospective_shadow_review import summarize

NOW=datetime(2026,10,13,14,0,tzinfo=timezone.utc)


def hyp(side="BUY",symbol="XAUUSD.vx",t=NOW):
    stop,target=(99.,103.) if side=="BUY" else (101.2,97.)
    return ResearchHypothesis(
        symbol=symbol,method="TREND_PULLBACK",
        regime="TREND_UP" if side=="BUY" else "TREND_DOWN",
        side=side,closed_bar_at=t-timedelta(minutes=5),
        observed_at=t,bid=100.,ask=100.1,tick_at=t.timestamp(),
        stop=stop,target=target,evidence_score=.8,
        blockers=("macro_not_verified","zero_live_permission"),
        official_news_verified=False,spread_atr=.05)


def verify(repo_root):
    from katarina.intelligence.news.verified_policy_context import _host_ok
    from katarina.intelligence.news.market_article_context import market_headline_relevant
    # Test policy source provenance and noisy social headlines.
    assert _host_ok("https://www.federalreserve.gov/newsevents/pressreleases/a.htm","fed")
    assert not _host_ok("https://www.federalreserve.gov.evil.example/a.htm","fed")
    assert market_headline_relevant("Global oil prices rise on supply disruption")
    assert not market_headline_relevant("Lawmaker personal scandal and news inquiry")

    db=sqlite3.connect(":memory:")
    try:
        book=ProspectiveShadowBook(db)
        s1=book.propose([hyp()],NOW)
        assert s1["accepted"] and s1["mode"]=="NO_REAL_ORDERS"
        second=book.propose([hyp(symbol="EURUSD.vx")],NOW)
        assert second["reason"]=="ONE_VIRTUAL_PORTFOLIO_POSITION_AT_A_TIME"
        exit_at=NOW+timedelta(minutes=5)
        close=book.settle(now=exit_at,quotes={
            "XAUUSD.vx":(103.4,103.6,exit_at.timestamp())})
        assert close==[("XAUUSD.vx","VIRTUAL_QUOTED")]
        after=exit_at+timedelta(minutes=5)
        book.propose([hyp(side="SELL",t=after)],after)
        late=after+timedelta(minutes=15)
        book.settle(now=late,quotes={
            "XAUUSD.vx":(95.,95.1,late.timestamp())})
        memory=summarize(db,late)
        statuses={k["diagnostic_status"] for k in memory["groups"]}
        assert statuses=={"INSUFFICIENT_SAMPLE"}
        result=book.summary()
        assert result["counts"]=={"UNCERTAIN_GAP":1,"VIRTUAL_QUOTED":1}
        assert result["orders_submitted"]==0
        assert result["usable_for_live_model_promotion"] is False
    finally:
        db.close()
    cli=(repo_root/"scripts/ai/run_contextual_market_observer.py").read_text()
    brain=(repo_root/"src/katarina/intelligence/cognition/unified_brain.py").read_text()
    observer=(repo_root/"src/katarina/intelligence/cognition/observer.py").read_text()
    assert "UnifiedKatarinaBrain.observe_once(" in cli
    assert "terminal_info()" in brain and "observation_permission(broker,terminal)" in brain
    assert "FAIL_CLOSED_TRADING_MUST_BE_DISABLED" in brain
    assert "lock_worker(" in brain and "lock.close()" in brain
    assert "ProspectiveShadowBook(" in brain
    assert "collect_market_articles(" in observer
    assert "self.shadow_book.settle(" in brain and "self.shadow_book.propose(" in brain
    for source in (cli, brain, observer):
        assert "order_send(" not in source
        assert "order_check(" not in source
    return {
        "status":"PASS_SYNTHETIC_SOFTWARE_SAFETY_ONLY",
        "verified_guards":[
            "single_canonical_observer_lock",
            "read_only_disabled_mt5_ordering_gate",
            "provenance_checked_official_rate_article",
            "secondary_news_financial_relevance_filter",
            "conditional_market_context_to_virtual_hypothesis",
            "only_one_virtual_exposure",
            "buy_ask_entry_bid_exit_cost_stress",
            "unobservable_tick_gap_disqualified",
            "past_only_virtual_memory_insufficient",
            "zero_live_execution_permission",
        ],
        "fixture_data":"SYNTHETIC_NOT_REAL_BROKER_HISTORY",
        "fixture_virtual_book":result,
        "fixture_memory":memory,
        "historical_market_edge_proven":False,
        "real_broker_costs_reconciled":False,
        "independent_forward_trade_sample_sufficient":False,
        "stage38_live_authorized":False,
        "orders_sent":0,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    root=Path(__file__).resolve().parents[2]
    result=verify(root)
    destination=Path(args.output)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("KATARINA_AUTONOMY_RUNNER_SAFETY",result["status"],
          "controls",len(result["verified_guards"]),"orders",result["orders_sent"])


if __name__=="__main__":
    main()
