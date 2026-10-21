# Multi-market brain observer v1 â€” 2026-10-10

## Delivered scope

The existing KatarinaAIBrain now exposes survey_markets. Its read-only runtime
discovers the entire broker symbol catalogue, records directional trade-mode
restrictions, retrieves 120 closed M1/M5 bars, computes relative ATR, EMA20/50,
directional efficiency and within-symbol tick activity, and scores volatility
against spread. Cross-symbol raw ATR is never used for ranking.

A maximum of five research candidates survive quote/history freshness, broker
permissions, spread/ATR <= 0.15, available external context and a conservative
absolute return-correlation limit of 0.8. Missing correlation overlap also blocks
an additional candidate. These are explicit research heuristics, not optimized
thresholds, calibrated probabilities, execution orders or portfolio-risk approval.

All outputs remain NO_TRADE until a separately validated symbol strategy and
execution profile exist. This observer does not place orders or promote models.
The existing chronological model trainer and gateway remain separate and retain
their previous validation/risk gates.

## External context and memory

Configured public sources:
- Federal Reserve: https://www.federalreserve.gov/feeds/press_all.xml
- ECB: https://www.ecb.europa.eu/rss/press.html
- Bank of England: https://www.bankofengland.co.uk/rss/news
- Forex Factory weekly export: https://nfs.faireconomy.media/ff_calendar_thisweek.json

News coverage is currently USD/EUR/GBP official releases. This is not full
coverage of every currency, geopolitical event, equity, commodity or crypto.
Uncovered currencies are explicit blockers, never silently treated as safe.

Calendar coverage is limited to the export week and supported currencies.
Impact events block from 30 minutes before to 15 minutes after publication time.
All overlapping events are checked. The old EconomicFeedGate nearest-event bug
was corrected: an event 16 minutes ago must not hide another event 20 minutes ahead.
Disabled and close-only broker trade modes are excluded from new-position scope.

The export's forecast/previous fields are preserved with their original units.
Actual values are nullable; unavailable actual values are never invented.
No directional sentiment or economic surprise is inferred without a calibrated
model and suitable actual/forecast data. Upcoming calendar events are known
schedules; future news publications are excluded.

SQLite keeps retrieval versions with SHA256, raw payload, first availability
time, parse/fetch status and immutable decision observations. Revisions cannot
be backdated into historical evaluation. Failed fetches do not freshen old data.
Identical bar histories are content-addressed once to limit repeated disk use.
The status JSON is replaced atomically; an OS lock prevents duplicate workers.

TLS verification remains enabled. certifi supplies a maintained CA bundle.
Network requests have timeouts, payload size caps and a 15-minute minimum fetch
interval. News TTL is 30 minutes; calendar TTL is one hour. No credentials are
required for these feeds. Retrieved text is untrusted data, not instructions.
RSS absence of a new headline is distinct from a failed feed request.

## Running on the VPS

Use the dedicated environment and research terminal:
- Python: C:\KatarinaDev\brain-runtime\Scripts\python.exe
- Terminal: C:\Program Files\MetaTrader 5 ALFA\terminal64.exe
- State: C:\KatarinaDev\artifacts\multi-market-brain
- Entrypoint: scripts/ai/run_market_brain.py

Install dependencies from requirements-brain-observer.txt. Run with --terminal
and --state-dir; default is one cycle. --cycles 0 enables a continuous process.
Install-MarketBrainObserver.ps1 creates a five-minute Windows scheduled task,
Katarina-MarketBrain-Observer, without overwriting an existing task.
The repetition trigger has a 3650-day horizon.
It uses the current user's interactive session, not a new account or stored
password. It does not promise operation before that user logs on after reboot.

Stop the scheduled observer before running experiments that need the same
research terminal. Existing MT5 tester guards must remain in place.
The collector adds subscriptions only in that research terminal.
To pause: Disable-ScheduledTask -TaskName Katarina-MarketBrain-Observer.
To inspect: Get-ScheduledTaskInfo -TaskName Katarina-MarketBrain-Observer.

## Evidence and remaining limits

69 intelligence unit tests and 9 brain integration tests passed (78 total).
The installed scheduled task completed its first run with result code 0.
See docs/validation/2026-10-10-multi-market-brain.json for real capture results.
The first actual broker catalogue contained 74 symbols. This Saturday's quotes
were stale or unavailable; no tradable opportunity was inferred from them.
Rejected future/duplicate bars are retained as explicit data-quality failures.

The Python bridge does not expose verified broker session schedules here.
Session verification, commission/slippage calibration, full news coverage,
event actuals/surprise modelling, symbol-specific validated strategies and
market-open forward observation remain necessary before trading readiness.
No profitable AI model or complete autonomous news reasoning is claimed.

## Primary references

- Broker symbol enumeration:
  https://www.mql5.com/en/docs/python_metatrader5/mt5symbolsget_py
- Closed-bar indexing (bar zero is current):
  https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py
- Fed RSS catalogue: https://www.federalreserve.gov/feeds/feeds.htm
- ECB RSS catalogue: https://www.ecb.europa.eu/home/html/rss.en.html
- Calendar weekly export: https://www.forexfactory.com/calendar

The observer's live October snapshots are forward observation records only.
They have not been used to retune the previous Januaryâ€“September experiments.
