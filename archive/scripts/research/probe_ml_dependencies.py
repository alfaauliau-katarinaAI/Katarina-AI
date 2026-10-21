import importlib.util,json
print(json.dumps({k:bool(importlib.util.find_spec(k)) for k in ("sklearn","numpy","pandas","MetaTrader5","scipy")}))
