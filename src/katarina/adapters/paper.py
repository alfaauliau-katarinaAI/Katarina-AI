from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class PaperOrder:
    order_id: str
    side: str
    requested_price: float
    volume: float
@dataclass(frozen=True, slots=True)
class PaperFill:
    order_id: str
    fill_price: float
    volume: float
    cost: float

class PaperExecutionVenue:
    def __init__(self, *, slippage_bps: float=0.5, commission_per_lot: float=0.0):
        self.slippage_bps=slippage_bps; self.commission_per_lot=commission_per_lot
    def execute(self, order: PaperOrder) -> PaperFill:
        if order.side not in {"BUY","SELL"} or order.volume<=0 or order.requested_price<=0: raise ValueError("invalid_order")
        sign=1 if order.side=="BUY" else -1
        fill=order.requested_price*(1+sign*self.slippage_bps/10000.0)
        return PaperFill(order.order_id,fill,order.volume,abs(order.volume)*self.commission_per_lot)
