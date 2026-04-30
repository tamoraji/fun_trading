"""Textual TUI dashboard for live trading monitoring."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer, Static, RichLog
from textual import work


class TradingDashboard(App):
    """Live-updating terminal dashboard for the trading engine."""

    CSS = """
    #portfolio {
        width: 1fr;
        height: 100%;
        border: solid green;
        padding: 1;
    }
    #strategies {
        width: 1fr;
        height: 100%;
        border: solid blue;
        padding: 1;
    }
    #top-row {
        height: 40%;
    }
    #signal-log {
        height: 60%;
        border: solid yellow;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "toggle_pause", "Pause/Resume"),
        ("s", "show_summary", "Summary"),
    ]

    def __init__(self, engine, settings):
        super().__init__()
        self.engine = engine
        self.settings = settings
        self.paused = False
        self.cycle_count = 0
        self._exit = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top-row"):
            yield Static("Loading...", id="portfolio")
            yield Static("Loading...", id="strategies")
        yield RichLog(id="signal-log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Trading Framework"
        self.sub_title = "Live Dashboard"
        self._run_engine()

    @work(thread=True, exit_on_error=False)
    def _run_engine(self) -> None:
        """Run engine cycles in a background thread."""
        while not self._exit:
            if not self.paused:
                self.cycle_count += 1

                log_messages: list[str] = []
                original_logger = self.engine.logger
                self.engine.logger = lambda msg: log_messages.append(msg)

                signals: list = []
                try:
                    signals = self.engine.run_cycle()
                except Exception as e:
                    log_messages.append(f"[error] Engine error: {e}")
                finally:
                    self.engine.logger = original_logger

                try:
                    self.call_from_thread(
                        self._update_ui, log_messages, signals
                    )
                except Exception:
                    break  # App is shutting down

            # Sleep in small increments so we can exit quickly
            for _ in range(self.settings.poll_interval_seconds):
                if self._exit:
                    return
                time.sleep(1)

    def _update_ui(self, log_messages: list[str], signals: list) -> None:
        """Update all dashboard panels (called on the UI thread)."""
        self._update_portfolio()
        self._update_strategies(log_messages, signals)
        self._update_signal_log(log_messages)

    def _update_portfolio(self) -> None:
        widget = self.query_one("#portfolio", Static)
        if self.engine.portfolio:
            p = self.engine.portfolio
            lines = [
                "[bold]PORTFOLIO[/bold]",
                f"Cash: ${p.cash:,.2f}",
                f"Realized P&L: ${p.realized_pnl():,.2f}",
                f"Orders: {len(p.orders)}",
                "",
            ]
            if p.positions:
                lines.append("[bold]Open Positions:[/bold]")
                for pos in p.positions.values():
                    lines.append(
                        f"  {pos.symbol}  {pos.side}  "
                        f"${pos.entry_price:.2f}  qty:{pos.quantity:.2f}"
                    )
            else:
                lines.append("No open positions")
            widget.update("\n".join(lines))
        else:
            widget.update("[bold]PORTFOLIO[/bold]\nPaper trading disabled")

    def _update_strategies(
        self, log_messages: list[str], signals: list
    ) -> None:
        widget = self.query_one("#strategies", Static)
        holds = sum(1 for m in log_messages if "[hold]" in m)
        risks = sum(1 for m in log_messages if "[risk]" in m)
        errors = sum(1 for m in log_messages if "[error]" in m)

        lines = [
            "[bold]STATUS[/bold]",
            f"Cycle: {self.cycle_count}",
            f"Symbols: {', '.join(self.settings.symbols)}",
            f"Poll: {self.settings.poll_interval_seconds}s",
            "",
            "[bold]Last Cycle:[/bold]",
            f"Signals: {len(signals)}",
            f"Holds: {holds}",
        ]
        if risks:
            lines.append(f"Risk blocked: {risks}")
        if errors:
            lines.append(f"Errors: {errors}")
        widget.update("\n".join(lines))

    def _update_signal_log(self, log_messages: list[str]) -> None:
        log_widget = self.query_one("#signal-log", RichLog)
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        for msg in log_messages:
            if "[cycle_start]" in msg or "[cycle_end]" in msg:
                log_widget.write(f"[dim]{timestamp}  {msg}[/dim]")
            elif "[signal]" in msg:
                log_widget.write(
                    f"[bold green]{timestamp}  {msg}[/bold green]"
                )
            elif "[paper]" in msg:
                log_widget.write(
                    f"[bold cyan]{timestamp}  {msg}[/bold cyan]"
                )
            elif "[risk]" in msg:
                log_widget.write(f"[yellow]{timestamp}  {msg}[/yellow]")
            elif "[error]" in msg:
                log_widget.write(
                    f"[bold red]{timestamp}  {msg}[/bold red]"
                )
            elif "[hold]" in msg:
                log_widget.write(f"[dim]{timestamp}  {msg}[/dim]")
            elif "[skip]" in msg:
                log_widget.write(
                    f"[dim italic]{timestamp}  {msg}[/dim italic]"
                )
            else:
                log_widget.write(f"{timestamp}  {msg}")

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        state = "PAUSED" if self.paused else "Running"
        self.sub_title = f"Live Dashboard — {state}"

    def action_show_summary(self) -> None:
        if self.engine.portfolio:
            log_widget = self.query_one("#signal-log", RichLog)
            log_widget.write("")
            log_widget.write("[bold]═══ PORTFOLIO SUMMARY ═══[/bold]")
            log_widget.write(self.engine.portfolio.summary())


    def action_quit(self) -> None:
        self._exit = True
        super().exit()

    def on_unmount(self) -> None:
        self._exit = True


def run_tui(settings) -> None:
    """Launch the TUI dashboard with the given settings."""
    from .cli import build_engine_from_settings

    engine = build_engine_from_settings(settings, pretty=False)
    engine.logger = lambda msg: None

    app = TradingDashboard(engine, settings)
    try:
        app.run()
    except KeyboardInterrupt:
        app._exit = True

    # Save portfolio on exit
    if engine.portfolio:
        engine.portfolio.save(settings.paper_portfolio_path)
        print(f"\nPortfolio saved to {settings.paper_portfolio_path}")
