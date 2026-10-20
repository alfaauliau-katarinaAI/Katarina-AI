"""Explicit opt-in coexistence of read-only sensors and a demo executor."""


def observation_permission(broker, terminal=None):
    terminal = terminal if terminal is not None else broker.terminal_info()
    if terminal is None:
        return False
    if getattr(terminal, 'trade_allowed', None) is False:
        return True
    if getattr(broker, 'demo_observation_enabled', None) is not True:
        return False
    account = broker.account_info()
    flag = getattr(broker, 'ACCOUNT_TRADE_MODE_DEMO', None)
    return (getattr(terminal, 'trade_allowed', None) is True
            and type(flag) is int and account is not None
            and type(getattr(account, 'trade_mode', None)) is int
            and account.trade_mode == flag)


def monitor_permission(monitor):
    return (monitor.get('algo_trading_off') is True
            or (monitor.get('algo_trading_off') is False
                and monitor.get('demo_observation_enabled') is True
                and monitor.get('account_mode') == 'DEMO'))
