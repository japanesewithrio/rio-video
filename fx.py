"""USD/JPY daily report + paper-trading bot (no real money).
Strategy: 1h EMA20/EMA50 trend + RSI filter, ATR stop, fixed $10 risk per trade,
daily loss limit $30 (JST day). State is kept in fx/state.json."""
import json, os, datetime as dt
import numpy as np, pandas as pd, yfinance as yf

RISK_PER_TRADE = 10.0     # USD lost if stop is hit
DAILY_LOSS_LIMIT = 30.0   # USD, bot stops for the rest of the JST day
START_BALANCE = 1000.0
JST = dt.timezone(dt.timedelta(hours=9))
ST = "fx/state.json"


def load_state():
    if os.path.exists(ST):
        return json.load(open(ST))
    return {"balance": START_BALANCE, "position": None, "last_ts": None,
            "day": None, "day_pnl": 0.0, "halted": False, "trades": []}


def indicators(df):
    c = df["Close"]
    df["ema20"] = c.ewm(span=20, adjust=False).mean()
    df["ema50"] = c.ewm(span=50, adjust=False).mean()
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    df["rsi"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - c.shift()).abs(), (df["Low"] - c.shift()).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    return df


def step(s, ts, t, r):
        day = ts.tz_convert(JST).strftime("%Y-%m-%d") if ts.tzinfo else ts.strftime("%Y-%m-%d")
        if day != s["day"]:
            s["day"], s["day_pnl"], s["halted"] = day, 0.0, False
        pos = s["position"]
        if pos:
            if pos["side"] == "buy":
                if r["Low"] <= pos["stop"]:
                    close_pos(s, pos, pos["stop"], t, "stop")
                elif r["High"] >= pos["tp"]:
                    close_pos(s, pos, pos["tp"], t, "target")
            else:
                if r["High"] >= pos["stop"]:
                    close_pos(s, pos, pos["stop"], t, "stop")
                elif r["Low"] <= pos["tp"]:
                    close_pos(s, pos, pos["tp"], t, "target")
        if not s["position"] and not s["halted"] and not np.isnan(r["atr"]):
            side = None
            if r["ema20"] > r["ema50"] and 50 < r["rsi"] < 70 and r["Close"] > r["ema20"]:
                side = "buy"
            elif r["ema20"] < r["ema50"] and 30 < r["rsi"] < 50 and r["Close"] < r["ema20"]:
                side = "sell"
            if side:
                dist = 1.5 * r["atr"]
                price = float(r["Close"])
                units = RISK_PER_TRADE * price / dist
                s["position"] = {"side": side, "entry": round(price, 3), "units": round(units),
                                 "stop": round(price - dist if side == "buy" else price + dist, 3),
                                 "tp": round(price + 2 * dist if side == "buy" else price - 2 * dist, 3), "ts": t}
        s["last_ts"] = t


def close_pos(s, pos, price, ts, why):
    pnl_jpy = (price - pos["entry"]) * pos["units"] * (1 if pos["side"] == "buy" else -1)
    pnl = pnl_jpy / price
    s["balance"] = round(s["balance"] + pnl, 2)
    s["day_pnl"] = round(s["day_pnl"] + pnl, 2)
    s["trades"].append({"side": pos["side"], "entry": pos["entry"], "exit": round(price, 3),
                        "open": pos["ts"], "close": ts, "pnl": round(pnl, 2), "why": why})
    s["position"] = None
    if s["day_pnl"] <= -DAILY_LOSS_LIMIT:
        s["halted"] = True


def simulate(df, s):
    for ts, r in df.iloc[60:].iterrows():
        t = ts.isoformat()
        if s["last_ts"] and t <= s["last_ts"]:
            continue
        step(s, ts, t, r)
    return s


def run():
    df = yf.download("USDJPY=X", period="30d", interval="1h", progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = indicators(df.dropna(subset=["Close"]))
    fresh = not os.path.exists(ST)
    bt = simulate(df, {"balance": START_BALANCE, "position": None, "last_ts": None,
                       "day": None, "day_pnl": 0.0, "halted": False, "trades": []})
    s = load_state()
    if fresh:
        s["last_ts"] = df.index[-1].isoformat()
    simulate(df, s)
    s["trades"] = s["trades"][-200:]
    last = df.iloc[-1]
    d24 = df[df.index >= df.index[-1] - pd.Timedelta(hours=24)]
    closed = [x for x in s["trades"] if x["close"] >= (df.index[-1] - pd.Timedelta(hours=24)).isoformat()]
    rep = {
        "time_jst": dt.datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "price": round(float(last["Close"]), 3),
        "change_24h": round(float(last["Close"] - d24["Close"].iloc[0]), 3),
        "high_24h": round(float(d24["High"].max()), 3), "low_24h": round(float(d24["Low"].min()), 3),
        "week_change": round(float(last["Close"] - df["Close"].iloc[-120]), 3) if len(df) > 120 else None,
        "trend": "up" if last["ema20"] > last["ema50"] else "down",
        "rsi": round(float(last["rsi"]), 1), "atr": round(float(last["atr"]), 3),
        "paper": {"balance": s["balance"], "start": START_BALANCE, "day_pnl": s["day_pnl"],
                  "halted_today": s["halted"], "open_position": s["position"],
                  "trades_24h": closed, "total_trades": len(s["trades"]),
                  "win_rate": round(100 * sum(1 for x in s["trades"] if x["pnl"] > 0) / len(s["trades"]), 1) if s["trades"] else None,
                  "backtest_30d": {"trades": len(bt["trades"]), "pnl": round(bt["balance"] - START_BALANCE, 2),
                                   "win_rate": round(100 * sum(1 for x in bt["trades"] if x["pnl"] > 0) / len(bt["trades"]), 1) if bt["trades"] else None},
                  "rules": "EMA20/EMA50 trend + RSI, stop 1.5xATR, target 3xATR, $10 risk/trade, stop for the day at -$30"},
    }
    json.dump(s, open(ST, "w"), indent=1)
    json.dump(rep, open("fx/report.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    os.makedirs("fx", exist_ok=True)
    run()
