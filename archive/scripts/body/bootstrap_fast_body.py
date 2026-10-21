from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STAGES = {
    11: dict(name="Market Intelligence Engine", deps=[10], authority="analytic", policy=False, windows=False,
             query="vectorized market features indicators signals",
             ref="https://github.com/polakowo/vectorbt/blob/ceffc501f2d37033a79dd86a9f883e69ec6977bd/docs/docs/getting-started/features.md"),
    12: dict(name="Multi-Timeframe Engine", deps=[11], authority="analytic", policy=False, windows=False,
             query="multi timeframe data replay resampling",
             ref="https://github.com/mementum/backtrader/blob/b853d7c90b6721476eb5a5ea3135224e33db1f14/samples/data-multitimeframe/data-multitimeframe.py"),
    13: dict(name="Market Regime Engine", deps=[11, 12], authority="analytic", policy=False, windows=False,
             query="market regime volatility trend classification architecture",
             ref="https://github.com/OnePunchMonk/AgentQuant/blob/b8103bf356a51303952f23daa656cd035dcd7850/DESIGN.md"),
    14: dict(name="XAUUSD Specialist V1", deps=[11, 12, 13], authority="advisory", policy=True, windows=False,
             query="XAUUSD specialist signal engine architecture",
             ref="https://github.com/francomascareloai/EA_SCALPER_XAUUSD/blob/b0087e93c8af6690102c6698b8123186703a9240/DOCS/04_REPORTS/CLOUD_ARCHITECTURE_DESIGN.md"),
    15: dict(name="Decision Engine", deps=[14], authority="advisory", policy=True, windows=False,
             query="trading strategy decision signal callback architecture",
             ref="https://github.com/freqtrade/freqtrade/blob/338e264643c113642a69e44094870ccb0d84bdb8/docs/strategy-101.md"),
    16: dict(name="Risk Governor", deps=[15], authority="governance", policy=True, windows=False,
             query="trading risk engine limits governor kill switch",
             ref="https://github.com/nautechsystems/nautilus_trader/blob/009ca1f1d99fde9595059fd4471e54bde1d76bf4/crates/risk/src/engine/config.rs"),
    17: dict(name="Position Sizing Engine", deps=[16], authority="governance", policy=True, windows=False,
             query="position sizing sizer percent risk architecture",
             ref="https://github.com/mementum/backtrader/blob/b853d7c90b6721476eb5a5ea3135224e33db1f14/backtrader/sizer.py"),
    18: dict(name="Execution Engine", deps=[15, 16, 17], authority="execution_path", policy=False, windows=False,
             query="execution engine order lifecycle idempotent trading",
             ref="https://github.com/nautechsystems/nautilus_trader/blob/009ca1f1d99fde9595059fd4471e54bde1d76bf4/crates/execution/src/engine/config.rs"),
    19: dict(name="Position Manager", deps=[18], authority="execution_path", policy=False, windows=False,
             query="position management stoploss lifecycle callbacks",
             ref="https://github.com/freqtrade/freqtrade/blob/338e264643c113642a69e44094870ccb0d84bdb8/docs/strategy-callbacks.md"),
    20: dict(name="Trade Evaluation Engine", deps=[19], authority="analytic", policy=False, windows=False,
             query="trade performance evaluation drawdown sharpe metrics",
             ref="https://github.com/ranaroussi/quantstats/blob/9ef4c6d0a4ffe7831f6ebba6a5824fd33a90c05a/quantstats/stats.py"),
    21: dict(name="Research Engine", deps=[20], authority="analytic", policy=False, windows=False,
             query="vectorized quantitative research portfolio analysis",
             ref="https://github.com/polakowo/vectorbt/blob/ceffc501f2d37033a79dd86a9f883e69ec6977bd/README.md"),
    22: dict(name="Backtesting Engine", deps=[20, 21], authority="analytic", policy=False, windows=False,
             query="backtesting engine broker strategy runner",
             ref="https://github.com/mementum/backtrader/blob/b853d7c90b6721476eb5a5ea3135224e33db1f14/backtrader/cerebro.py"),
    23: dict(name="Out-of-Sample + Walk-Forward", deps=[22], authority="analytic", policy=False, windows=False,
             query="walk forward analysis out of sample trading backtest",
             ref="https://github.com/Grademark/grademark/blob/dee7bb1a6fd27cf5c11e8116995ba359579d041e/README.md"),
    24: dict(name="Monte Carlo / Robustness", deps=[22, 23], authority="analytic", policy=False, windows=False,
             query="monte carlo trading robustness drawdown simulation",
             ref="https://github.com/ranaroussi/quantstats/blob/9ef4c6d0a4ffe7831f6ebba6a5824fd33a90c05a/docs/montecarlo.md"),
    25: dict(name="Tester Evaluation", deps=[18, 19, 20], authority="advisory", policy=False, windows=False,
             query="strategy tester simulated execution offline evaluation trading",
             ref="https://github.com/maadjiba24-afk/Olympus-/blob/2723488e065029406152fcc41995deace0e9c4ff/docs/TRADING_ARCHITECTURE.md"),
    26: dict(name="Learning Engine", deps=[20, 21, 25], authority="analytic", policy=False, windows=False,
             query="online learning incremental learn predict architecture",
             ref="https://github.com/online-ml/river/blob/086e8028b4867ee7dbc40d4e7b9886c5fe80f4a7/river/tree/stochastic_gradient_tree.py"),
    27: dict(name="Machine Learning V1", deps=[23, 24, 26], authority="analytic", policy=False, windows=False,
             query="trading machine learning feature training model pipeline",
             ref="https://github.com/freqtrade/freqtrade/blob/338e264643c113642a69e44094870ccb0d84bdb8/docs/freqai.md"),
    28: dict(name="Model Promotion & Rollback", deps=[24, 27], authority="governance", policy=False, windows=False,
             query="model registry promotion rollback champion aliases",
             ref="https://github.com/mlflow/mlflow/blob/d42618aad0650742429443f84acccb6f132e7e0b/docs/docs/classic-ml/model-registry/index.mdx"),
    29: dict(name="Economic Intelligence Engine", deps=[11, 13], authority="analytic", policy=False, windows=False,
             query="economic intelligence macro FRED OpenBB provider",
             ref="https://github.com/TerminalSkills/skills/blob/a021875c0f1bd906248e3784ce470faa65055201/skills/openbb/SKILL.md"),
    30: dict(name="Portfolio & Multi-Pair Engine", deps=[16, 20, 29], authority="governance", policy=False, windows=False,
             query="portfolio optimization efficient frontier covariance weights",
             ref="https://github.com/PyPortfolio/PyPortfolioOpt/blob/a6638d2e06dae6f444fd022cfd4b3c528902a85b/docs/GeneralEfficientFrontier.rst"),
    31: dict(name="Correlation & Global Exposure Engine", deps=[30], authority="governance", policy=False, windows=False,
             query="correlation covariance exposure portfolio risk",
             ref="https://github.com/dcajasn/Riskfolio-Lib/blob/7b1b26ac9760974c12ecefe290a9d3bd37b66b7a/riskfolio/src/HCPortfolio.py"),
    32: dict(name="Dashboard", deps=[20, 31], authority="observability", policy=False, windows=False,
             query="trading dashboard realtime portfolio metrics streamlit",
             ref="https://github.com/LeoRigasaki/stock-market-prediction-engine/blob/ce87a8645643683e86b80e0d8883fc58780297bf/src/streamlit_dashboard.py"),
    33: dict(name="Automated Testing / CI", deps=[9], authority="governance", policy=False, windows=False,
             query="python trading pytest github actions CI",
             ref="https://github.com/freqtrade/freqtrade/blob/338e264643c113642a69e44094870ccb0d84bdb8/.github/workflows/ci.yml"),
    34: dict(name="Constitution Guard", deps=[9, 33], authority="governance", policy=False, windows=False,
             query="policy as code invariant guard deny fail closed",
             ref="https://github.com/OrodruinLabs/nazgul/blob/1d388c87e845fbfab14071fac85157fa026f9534/RULES.md"),
    35: dict(name="MT5 Strategy Tester Integration", deps=[18, 22, 33], authority="analytic", policy=False, windows=True,
             query="MetaTrader 5 strategy tester automation MQL5",
             ref="https://github.com/terrylica/mql5-crossover/blob/0c4bf7b36e922e8a19947463af1659b63042f4a5/docs/plans/STRATEGY_TESTER_BLOCKING_ISSUE.md"),
    36: dict(name="Live Environment Preflight", deps=[25, 34, 35], authority="governance", policy=False, windows=True,
             query="live trading preflight broker connection health reconciliation risk gate",
             ref="https://github.com/SvilarT/AUTONOMOUS-TRADING-BOT/blob/98fe2ebf31be22a8ccdf3b934ddca315fba6692f/docs/PHASE_4_MANUAL_LIVE_TRADING_READINESS.md"),
    37: dict(name="Stress Test", deps=[24, 35, 36], authority="governance", policy=False, windows=False,
             query="trading engine stress test failure injection",
             ref="https://github.com/akramahmed1/quantenergx/blob/f8ca6a927222133f509facd1fd530ebfaa1d6143/TESTING.md"),
    38: dict(name="Live Micro-Risk Validation", deps=[16, 34, 36, 37], authority="governance", policy=True, windows=True,
             query="bounded live trading canary micro risk validation",
             ref="https://github.com/Dejetins/roehub.com/blob/6d7f0a31fa7225f34df816a917ca93a57fb564c3/.codex/agents/generated/rl-trading-agent-platform-v1/20-bounded-mainnet-canary.md"),
    39: dict(name="Performance Monitoring", deps=[32, 36, 37], authority="observability", policy=False, windows=False,
             query="trading monitoring prometheus latency errors metrics",
             ref="https://github.com/triqbit/mt5-ai-xauusd-trader/blob/55050974d210890c6195644c51685f912e17900c/MONITORING_ALERTING.md"),
    40: dict(name="Continuous Evolution", deps=[26, 28, 33, 34, 39], authority="governance", policy=False, windows=False,
             query="continuous learning retraining monitoring rollback evolution",
             ref="https://github.com/SyedNaveedM/CampusX_ML/blob/5f7e8bec859d654b8ded0ec11c9626da30a8b33d/005_Online_Learning/notes.md"),
}

MODULE_TEMPLATE = '''# GENERATED BY scripts/body/bootstrap_fast_body.py
from __future__ import annotations

from katarina.body.component import PassiveStageComponent
from katarina.body.contracts import AuthorityClass, BodyStatus, StageSpec


class Component(PassiveStageComponent):
    SPEC = StageSpec(
        stage={stage},
        name={name!r},
        dependencies={deps!r},
        authority=AuthorityClass.{authority},
        policy_pending={policy},
        windows_required={windows},
        implementation_module={module!r},
        reference_doc={reference_doc!r},
        status=BodyStatus.BODY_FRAMEWORK_COMPLETE,
        live_risk_ready=False,
        live_execution_authority=False,
    )
'''


def write_generated(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if old and "GENERATED BY scripts/body/bootstrap_fast_body.py" not in old:
            raise RuntimeError(f"refusing to overwrite non-generated file: {path}")
    path.write_text(content, encoding="utf-8")


def main() -> None:
    manifest_dir = ROOT / "config" / "stages"
    research_dir = ROOT / "docs" / "research" / "stages"
    module_dir = ROOT / "src" / "katarina" / "body"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    module_dir.mkdir(parents=True, exist_ok=True)

    for stage, spec in STAGES.items():
        slug = f"stage{stage:02d}"
        module = f"katarina.body.{slug}"
        refdoc = f"docs/research/stages/STAGE_{stage:02d}_GITHUB_REFERENCES.md"
        manifest = {
            "stage": stage,
            "name": spec["name"],
            "dependencies": spec["deps"],
            "authority": spec["authority"],
            "policy_pending": spec["policy"],
            "windows_required": spec["windows"],
            "implementation_module": module,
            "reference_doc": refdoc,
            "status": "body_framework_complete",
            "live_risk_ready": False,
            "live_execution_authority": False,
            "github_reference_query": spec["query"],
            "github_reference_url": spec["ref"],
        }
        (manifest_dir / f"{slug}.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        authority_const = {
            "analytic": "ANALYTIC",
            "advisory": "ADVISORY",
            "governance": "GOVERNANCE",
            "execution_path": "EXECUTION_PATH",
            "observability": "OBSERVABILITY",
        }[spec["authority"]]
        write_generated(
            module_dir / f"{slug}.py",
            MODULE_TEMPLATE.format(
                stage=stage,
                name=spec["name"],
                deps=tuple(spec["deps"]),
                authority=authority_const,
                policy=spec["policy"],
                windows=spec["windows"],
                module=module,
                reference_doc=refdoc,
            ),
        )

        research = f"""# Stage {stage:02d} — GitHub Prior-Art Reference

Status: SEARCHED / REVIEW INPUT  
Stage: {spec['name']}

## Search intent

`{spec['query']}`

## Selected reference

{spec['ref']}

## KATARINA adaptation rule

- Reference is prior art only; code is not copied blindly.
- Frozen Stage 01-09 invariants remain authoritative.
- Python remains central intelligence.
- Strategy/risk policy is not silently finalized.
- Live risk and live execution authority remain disabled.
- The generated Stage {stage:02d} component is an integration body shell.
- Functional trading logic requires its own governed implementation and tests.

## Body-build result

`BODY_FRAMEWORK_COMPLETE`

This status means the stage has a stable integration boundary in the KATARINA
body. It does **not** mean production trading logic or live-risk validation is
finalized.
"""
        (research_dir / f"STAGE_{stage:02d}_GITHUB_REFERENCES.md").write_text(
            research, encoding="utf-8"
        )

    config = {
        "mode": "FAST_BODY_BUILD",
        "stage_range": [10, 40],
        "github_reference_required": True,
        "workspace": "local_first",
        "github_push": False,
        "strategy_policy_finalized": False,
        "risk_policy_finalized": False,
        "live_risk_ready": False,
        "live_execution_enabled": False,
        "body_framework_target": "Stage 40",
        "generated_stage_manifests": len(STAGES),
    }
    (ROOT / "config" / "body_build.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )

    print(f"generated {len(STAGES)} stage manifests, modules, and reference docs")
    upgrade = ROOT / "scripts" / "body" / "upgrade_functional_body.py"
    if upgrade.is_file():
        subprocess.run([sys.executable, str(upgrade)], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
