"""Research-only normalized cost/target economics.

NOT a trading signal. All distances use one consistent quoted-price unit.
The current historical markout archive has no SL/TP paths, real commissions,
or fill probabilities, so this can only calculate conditional break-even
requirements until an executable tick-path study exists.
"""
from __future__ import annotations
from math import isfinite

def hypothetical_trade_budget(*, spread, target_distance, stop_distance,
                              extra_roundtrip_cost=None,
                              estimated_hit_probability=None):
    """Evaluate theoretical net R/R and break-even win probability.

    The gross target and stop distances are measured from an entry *midpoint*.
    The full quoted round-trip spread approximates paying half spread at
    entry and half at exit. Additional fee/slippage is the same price unit.
    Missing extra costs are deliberately marked uncalibrated.
    """
    inputs=(spread,target_distance,stop_distance)
    if not all(isinstance(x,(int,float)) and isfinite(x) for x in inputs):
        raise ValueError("invalid_budget")
    if spread<0 or target_distance<=0 or stop_distance<=0:
        raise ValueError("invalid_budget")
    if extra_roundtrip_cost is not None and (
        not isinstance(extra_roundtrip_cost,(int,float)) or
        not isfinite(extra_roundtrip_cost) or extra_roundtrip_cost<0
    ):
        raise ValueError("invalid_extra_roundtrip_cost")
    if estimated_hit_probability is not None and (
        not isinstance(estimated_hit_probability,(int,float)) or
        not isfinite(estimated_hit_probability) or
        not 0<=estimated_hit_probability<=1
    ):
        raise ValueError("invalid_hit_probability")
    # Missing extra fees are never silently represented as zero real costs.
    total_known_cost=spread+(extra_roundtrip_cost or 0)
    net_win=target_distance-total_known_cost
    net_loss=stop_distance+total_known_cost
    positive_target=net_win>0
    breakeven=net_loss/(net_win+net_loss) if positive_target else None
    conditional_r_multiple=(net_win/net_loss if positive_target else None)
    expectancy=(estimated_hit_probability*net_win-
                (1-estimated_hit_probability)*net_loss) if (
                    estimated_hit_probability is not None and positive_target
                    and extra_roundtrip_cost is not None) else None
    enough=(extra_roundtrip_cost is not None and
            estimated_hit_probability is not None)
    return dict(kind="conditional_cost_budget_not_backtest",
        spread_to_target=spread/target_distance,
        known_cost_to_target=total_known_cost/target_distance,
        net_win_price_units=net_win,
        net_loss_price_units=net_loss,
        conditional_net_reward_risk=conditional_r_multiple,
        breakeven_hit_probability=breakeven,
        estimated_hit_probability=estimated_hit_probability,
        calibrated_extra_roundtrip_cost_available=extra_roundtrip_cost is not None,
        calibrated_probability_available=estimated_hit_probability is not None,
        expectancy_price_units=expectancy,
        positive_target_after_known_cost=positive_target,
        inputs_complete_for_hypothetical_expectancy=enough,
        trade_approved=False,
        live_execution_enabled=False,
        model_promotion_allowed=False,
        note="Even complete inputs require broker fees, tick-path backtest, uncertainty and out-of-sample checks before trading.",
    )
