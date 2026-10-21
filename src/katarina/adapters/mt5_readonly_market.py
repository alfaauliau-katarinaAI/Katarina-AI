"""External broker sensor adapter, injected; never imports or starts MT5."""
from datetime import datetime, timezone, timedelta

from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle

TF = {"M5":("TIMEFRAME_M5",5), "M15":("TIMEFRAME_M15",15), "H1":("TIMEFRAME_H1",60)}


def bars_for(broker, symbol: str, clock_correction: timedelta):
    result = {}
    for label, (frame_name, minutes) in TF.items():
        rates = broker.copy_rates_from_pos(symbol, getattr(broker, frame_name), 1, 130)
        if rates is None or len(rates) < 55:
            raise ValueError("insufficient_closed_" + label)
        result[label] = [
            SensorCandle(datetime.fromtimestamp(int(x["time"]), timezone.utc)
                         - clock_correction + timedelta(minutes=minutes),
                         float(x["open"]), float(x["high"]), float(x["low"]),
                         float(x["close"]), float(x["tick_volume"])) for x in rates
        ]
    return result
