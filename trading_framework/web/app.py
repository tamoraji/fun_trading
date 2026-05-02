from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Trading Framework")
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(templates_dir))
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

_DEFAULT_WATCHLIST = ["AAPL", "MSFT", "SPY", "BTC-USD", "GOOGL", "TSLA", "AMZN", "ETH-USD"]


def _load_portfolio():
    from ..paper import PaperPortfolio
    path = "paper_portfolio.json"
    if Path(path).exists():
        return PaperPortfolio.load(path)
    return None


def _load_signals(limit=50):
    from ..history import JsonLinesHistory
    history = JsonLinesHistory("signal_history.jsonl")
    records = history.read_all()
    return records[-limit:]


def _get_provider():
    from ..data import create_market_data_provider
    from ..models import MarketDataConfig
    from ..cache import CachedDataProvider
    config = MarketDataConfig(bar_interval="1d", lookback="6mo")
    provider = CachedDataProvider(create_market_data_provider(config), cache_dir=".cache", ttl_seconds=3600)
    return provider, config


# --- MARKETS ---
@app.get("/", response_class=HTMLResponse)
@app.get("/markets", response_class=HTMLResponse)
async def markets_page(request: Request):
    provider, config = _get_provider()
    from ..analytics.regime import regime_summary

    watchlist = []
    for symbol in _DEFAULT_WATCHLIST:
        try:
            bars = provider.fetch_bars(symbol, config)
            summary = regime_summary(bars)
            last = bars[-1]
            prev = bars[-2] if len(bars) > 1 else last
            change_pct = ((last.close - prev.close) / prev.close * 100) if prev.close else 0
            watchlist.append({
                "symbol": symbol, "price": last.close, "change_pct": change_pct,
                "volume": last.volume, "regime": summary["regime"],
                "slope": summary["slope"], "vol_percentile": summary["vol_percentile"],
                "high": last.high, "low": last.low,
            })
        except Exception:
            watchlist.append({"symbol": symbol, "error": True})

    return templates.TemplateResponse(request, "markets.html", {"page": "markets", "watchlist": watchlist})


@app.get("/markets/chart/{symbol}", response_class=HTMLResponse)
async def symbol_chart(request: Request, symbol: str):
    provider, config = _get_provider()
    from ..analytics.regime import regime_summary

    try:
        bars = provider.fetch_bars(symbol.upper(), config)
        summary = regime_summary(bars)

        # Build candlestick + SMA + volume data
        dates = [b.timestamp.strftime("%Y-%m-%d") for b in bars]
        opens = [b.open for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        closes = [b.close for b in bars]
        volumes = [b.volume for b in bars]

        # SMA 20 and 50
        sma20 = [None] * 19 + [sum(closes[i - 19:i + 1]) / 20 for i in range(19, len(closes))]
        sma50 = [None] * 49 + [sum(closes[i - 49:i + 1]) / 50 for i in range(49, len(closes))]

        chart_data = json.dumps({
            "dates": dates, "opens": opens, "highs": highs, "lows": lows,
            "closes": closes, "volumes": volumes, "sma20": sma20, "sma50": sma50,
        })

        last = bars[-1]
        prev = bars[-2] if len(bars) > 1 else last
        change_pct = ((last.close - prev.close) / prev.close * 100) if prev.close else 0

        symbol_data = {
            "symbol": symbol.upper(), "price": last.close, "change_pct": change_pct,
            "high": last.high, "low": last.low, "volume": last.volume,
            "regime": summary["regime"], "slope": summary["slope"],
            "vol_percentile": summary["vol_percentile"],
        }
        error = None
    except Exception as e:
        chart_data = "{}"
        symbol_data = {"symbol": symbol.upper()}
        error = str(e)

    return templates.TemplateResponse(request, "symbol_chart.html", {
        "page": "markets", "symbol_data": symbol_data,
        "chart_data": chart_data, "error": error,
    })


# --- TRADING ---
@app.get("/trading", response_class=HTMLResponse)
async def trading_page(request: Request):
    signals = _load_signals(30)
    from ..interactive import STRATEGY_INFO
    return templates.TemplateResponse(request, "trading.html", {
        "page": "trading", "signals": signals,
        "strategies": {k: v["display_name"] for k, v in STRATEGY_INFO.items()},
    })


# --- BACKTEST LAB ---
@app.get("/backtest", response_class=HTMLResponse)
async def backtest_page(request: Request):
    from ..interactive import STRATEGY_INFO
    return templates.TemplateResponse(request, "backtest.html", {
        "page": "backtest",
        "strategies": {k: v["display_name"] for k, v in STRATEGY_INFO.items()},
        "results": None,
    })


@app.post("/backtest/run", response_class=HTMLResponse)
async def run_backtest_route(
    request: Request,
    symbol: str = Form(...),
    strategy: str = Form(...),
    lookback: str = Form("1y"),
):
    from ..data import create_market_data_provider
    from ..models import MarketDataConfig, StrategySettings
    from ..strategy import create_strategy
    from ..backtest import run_backtest
    from ..metrics import compute_metrics
    from ..interactive import STRATEGY_INFO
    from ..cache import CachedDataProvider
    from ..analytics.costs import CostModel, apply_costs, cost_summary as compute_cost_summary

    config = MarketDataConfig(provider="yahoo", bar_interval="1d", lookback=lookback, timeout_seconds=15)
    provider = CachedDataProvider(create_market_data_provider(config), cache_dir=".cache", ttl_seconds=300)

    strat_settings = StrategySettings(name=strategy, params={})
    strat = create_strategy(strat_settings)

    try:
        bars = provider.fetch_bars(symbol.upper(), config)
        bt_result = run_backtest(strat, symbol.upper(), bars)
        metrics = compute_metrics(bt_result.trades, bt_result.bars)

        cost_model = CostModel(slippage_pct=0.1, commission_per_trade=1.0)
        adjusted_trades = apply_costs(bt_result.trades, cost_model)
        cost_info = compute_cost_summary(bt_result.trades, adjusted_trades)

        # Candlestick chart data with BUY/SELL markers
        chart_data = json.dumps({
            "dates": [b.timestamp.strftime("%Y-%m-%d") for b in bars],
            "opens": [b.open for b in bars],
            "highs": [b.high for b in bars],
            "lows": [b.low for b in bars],
            "closes": [b.close for b in bars],
            "volumes": [b.volume for b in bars],
            "buy_dates": [s.timestamp.strftime("%Y-%m-%d") for s in bt_result.signals if s.action == "BUY"],
            "buy_prices": [s.price for s in bt_result.signals if s.action == "BUY"],
            "sell_dates": [s.timestamp.strftime("%Y-%m-%d") for s in bt_result.signals if s.action == "SELL"],
            "sell_prices": [s.price for s in bt_result.signals if s.action == "SELL"],
        })

        result = {
            "symbol": symbol.upper(),
            "strategy": STRATEGY_INFO.get(strategy, {}).get("display_name", strategy),
            "metrics": {
                "total_return": f"{metrics.total_return_pct:+.2f}%",
                "buy_hold": f"{metrics.buy_and_hold_return_pct:+.2f}%",
                "win_rate": f"{metrics.win_rate_pct:.1f}%",
                "num_trades": metrics.num_trades,
                "profit_factor": f"{metrics.profit_factor:.2f}" if metrics.profit_factor != float('inf') else "inf",
                "max_drawdown": f"-{metrics.max_drawdown_pct:.2f}%",
                "sharpe": f"{metrics.sharpe_ratio:.2f}",
            },
            "trades": [
                {"entry_date": t.entry_timestamp.strftime("%Y-%m-%d"), "action": t.entry_action,
                 "entry_price": f"{t.entry_price:,.2f}", "exit_price": f"{t.exit_price:,.2f}",
                 "pnl": f"{t.profit_pct:+.2f}%",
                 "days": (t.exit_timestamp - t.entry_timestamp).days}
                for t in bt_result.trades
            ],
            "chart_data": chart_data,
            "num_bars": len(bars),
            "start_date": bars[0].timestamp.strftime("%Y-%m-%d") if bars else "",
            "end_date": bars[-1].timestamp.strftime("%Y-%m-%d") if bars else "",
            "cost_info": {
                "original": f"{cost_info['original_return_pct']:+.2f}%",
                "adjusted": f"{cost_info['adjusted_return_pct']:+.2f}%",
                "cost": f"{cost_info['total_cost_pct']:+.2f}%",
            },
        }
        error = None
    except Exception as e:
        result = None
        error = str(e)

    return templates.TemplateResponse(request, "backtest.html", {
        "page": "backtest",
        "strategies": {k: v["display_name"] for k, v in STRATEGY_INFO.items()},
        "results": result, "error": error,
        "form_symbol": symbol, "form_strategy": strategy, "form_lookback": lookback,
    })


# --- PREDICTIONS ---
@app.get("/predictions", response_class=HTMLResponse)
async def predictions_page(request: Request):
    provider, config = _get_provider()
    from ..analytics.regime import regime_summary
    from ..analytics.ml.features import extract_features
    from ..analytics.ml.models import MomentumMLStrategy

    predictions = []
    ml = MomentumMLStrategy(lookback=20, buy_threshold=0.65, sell_threshold=0.35)

    for symbol in _DEFAULT_WATCHLIST[:6]:
        try:
            bars = provider.fetch_bars(symbol, config)
            summary = regime_summary(bars)
            features = extract_features(bars, lookback=20)
            last_features = features[-1] if features else {}
            signal = ml.evaluate(symbol, bars)

            predictions.append({
                "symbol": symbol,
                "regime": summary["regime"],
                "ml_score": signal.details.get("score", 0),
                "ml_action": signal.action,
                "rsi": last_features.get("rsi_14"),
                "volatility": last_features.get("volatility"),
                "volume_ratio": last_features.get("volume_ratio"),
                "trend": last_features.get("price_vs_sma"),
                "bollinger": last_features.get("bollinger_pct"),
            })
        except Exception:
            predictions.append({"symbol": symbol, "error": True})

    return templates.TemplateResponse(request, "predictions.html", {
        "page": "predictions", "predictions": predictions,
    })


# --- PORTFOLIO ---
@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page(request: Request):
    portfolio = _load_portfolio()
    portfolio_data = None
    if portfolio:
        portfolio_data = {
            "cash": portfolio.cash,
            "starting_cash": portfolio.starting_cash,
            "realized_pnl": portfolio.realized_pnl(),
            "num_orders": len(portfolio.orders),
            "positions": [
                {"symbol": p.symbol, "side": p.side, "entry_price": p.entry_price,
                 "quantity": p.quantity, "strategy": p.strategy_name,
                 "entry_date": p.entry_timestamp.strftime("%Y-%m-%d")}
                for p in portfolio.positions.values()
            ],
            "orders": [
                {"symbol": o.symbol, "action": o.action, "price": o.price,
                 "quantity": o.quantity, "timestamp": o.timestamp.strftime("%Y-%m-%d %H:%M"),
                 "pnl": o.pnl, "strategy": o.strategy_name}
                for o in portfolio.orders
            ],
        }
    return templates.TemplateResponse(request, "portfolio.html", {
        "page": "portfolio", "portfolio": portfolio_data,
    })


# --- SETTINGS ---
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    from ..interactive import STRATEGY_INFO, PRESETS
    return templates.TemplateResponse(request, "settings.html", {
        "page": "settings", "strategies": STRATEGY_INFO, "presets": PRESETS,
    })


# --- API endpoint for auto-refresh ---
@app.get("/api/signals", response_class=JSONResponse)
async def api_signals():
    return _load_signals(20)


def start_server(host="127.0.0.1", port=8000):
    """Start the web dashboard server."""
    import uvicorn
    print(f"\n  Dashboard: http://{host}:{port}")
    print("  Press Ctrl+C to stop.\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")
