from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Trading Framework Dashboard")

templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(templates_dir))

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# --- State (loaded on startup) ---
_portfolio: Optional[object] = None
_signal_history_path = "signal_history.jsonl"


def _load_portfolio():
    global _portfolio
    from ..paper import PaperPortfolio
    path = "paper_portfolio.json"
    if Path(path).exists():
        _portfolio = PaperPortfolio.load(path)
    else:
        _portfolio = None


def _load_signals(limit=50):
    from ..history import JsonLinesHistory
    history = JsonLinesHistory(_signal_history_path)
    records = history.read_all()
    return records[-limit:]  # most recent


@app.on_event("startup")
def startup():
    _load_portfolio()


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    _load_portfolio()
    signals = _load_signals(20)

    portfolio_data = None
    if _portfolio:
        portfolio_data = {
            "cash": _portfolio.cash,
            "starting_cash": _portfolio.starting_cash,
            "realized_pnl": _portfolio.realized_pnl(),
            "num_orders": len(_portfolio.orders),
            "positions": [
                {"symbol": p.symbol, "side": p.side, "entry_price": p.entry_price,
                 "quantity": p.quantity, "strategy": p.strategy_name}
                for p in _portfolio.positions.values()
            ],
            "recent_orders": [
                {"symbol": o.symbol, "action": o.action, "price": o.price,
                 "quantity": o.quantity, "timestamp": o.timestamp.isoformat(),
                 "pnl": o.pnl, "strategy": o.strategy_name}
                for o in _portfolio.orders[-10:]
            ],
        }

    return templates.TemplateResponse(request, "dashboard.html", {
        "page": "dashboard",
        "portfolio": portfolio_data,
        "signals": signals,
    })


@app.get("/market", response_class=HTMLResponse)
async def market_page(request: Request):
    """Market overview: regime detection for watchlist symbols."""
    from ..data import create_market_data_provider
    from ..models import MarketDataConfig
    from ..analytics.regime import regime_summary
    from ..cache import CachedDataProvider

    symbols = ["AAPL", "MSFT", "SPY", "BTC-USD", "GOOGL"]  # default watchlist
    config = MarketDataConfig(bar_interval="1d", lookback="6mo")
    provider = CachedDataProvider(create_market_data_provider(config), cache_dir=".cache", ttl_seconds=3600)

    market_data = []
    for symbol in symbols:
        try:
            bars = provider.fetch_bars(symbol, config)
            summary = regime_summary(bars)
            last_price = bars[-1].close if bars else 0
            market_data.append({
                "symbol": symbol,
                "price": last_price,
                "regime": summary["regime"],
                "slope": summary["slope"],
                "volatility": summary["volatility"],
                "vol_percentile": summary["vol_percentile"],
            })
        except Exception:
            market_data.append({"symbol": symbol, "error": True})

    return templates.TemplateResponse(request, "market.html", {
        "page": "market",
        "market_data": market_data,
    })


@app.get("/backtest", response_class=HTMLResponse)
async def backtest_page(request: Request):
    from ..interactive import STRATEGY_INFO, PRESETS
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

    config = MarketDataConfig(provider="yahoo", bar_interval="1d", lookback=lookback, timeout_seconds=15)
    provider = CachedDataProvider(create_market_data_provider(config), cache_dir=".cache", ttl_seconds=300)

    strat_settings = StrategySettings(name=strategy, params={})
    strat = create_strategy(strat_settings)

    try:
        bars = provider.fetch_bars(symbol.upper(), config)
        bt_result = run_backtest(strat, symbol.upper(), bars)
        metrics = compute_metrics(bt_result.trades, bt_result.bars)

        from ..analytics.costs import CostModel, apply_costs, cost_summary as compute_cost_summary

        cost_model = CostModel(slippage_pct=0.1, commission_per_trade=1.0)
        adjusted_trades = apply_costs(bt_result.trades, cost_model)
        cost_info = compute_cost_summary(bt_result.trades, adjusted_trades)

        # Build Plotly chart data
        chart_data = {
            "dates": [b.timestamp.strftime("%Y-%m-%d") for b in bars],
            "closes": [b.close for b in bars],
            "buy_dates": [s.timestamp.strftime("%Y-%m-%d") for s in bt_result.signals if s.action == "BUY"],
            "buy_prices": [s.price for s in bt_result.signals if s.action == "BUY"],
            "sell_dates": [s.timestamp.strftime("%Y-%m-%d") for s in bt_result.signals if s.action == "SELL"],
            "sell_prices": [s.price for s in bt_result.signals if s.action == "SELL"],
        }

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
            "chart_data": json.dumps(chart_data),
            "num_bars": len(bars),
            "start_date": bars[0].timestamp.strftime("%Y-%m-%d") if bars else "",
            "end_date": bars[-1].timestamp.strftime("%Y-%m-%d") if bars else "",
            "cost_info": cost_info,
        }
        error = None
    except Exception as e:
        result = None
        error = str(e)

    return templates.TemplateResponse(request, "backtest.html", {
        "page": "backtest",
        "strategies": {k: v["display_name"] for k, v in STRATEGY_INFO.items()},
        "results": result,
        "error": error,
        "form_symbol": symbol,
        "form_strategy": strategy,
        "form_lookback": lookback,
    })


@app.get("/strategies", response_class=HTMLResponse)
async def strategies_page(request: Request):
    from ..interactive import STRATEGY_INFO
    return templates.TemplateResponse(request, "strategies.html", {
        "page": "strategies",
        "strategies": STRATEGY_INFO,
    })


@app.get("/signals", response_class=HTMLResponse)
async def signals_page(request: Request):
    signals = _load_signals(100)
    return templates.TemplateResponse(request, "signals.html", {
        "page": "signals",
        "signals": signals,
    })


def start_server(host="127.0.0.1", port=8000):
    """Start the web dashboard server."""
    import uvicorn
    print(f"\n  Dashboard: http://{host}:{port}")
    print("  Press Ctrl+C to stop.\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")
