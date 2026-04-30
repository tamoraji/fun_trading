from __future__ import annotations

from datetime import datetime, timezone


class PrettyLogger:
    """Human-readable logger for interactive terminal sessions.

    Callable — drop-in replacement for the StructuredLogger / print logger.
    """

    def __init__(self) -> None:
        pass

    def __call__(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")

        if message.startswith("[cycle_start]"):
            symbols = message.split("symbols=", 1)[1] if "symbols=" in message else ""
            print(f"\n  {timestamp}  Polling {symbols}")
            return

        if message.startswith("[cycle_end]"):
            # Parse: [cycle_end] signals=0 holds=3 errors=0 elapsed=0.442s
            parts = message.replace("[cycle_end] ", "").split()
            info = {}
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    info[k] = v

            signals = info.get("signals", "0")
            holds = info.get("holds", "0")
            errors = info.get("errors", "0")
            elapsed = info.get("elapsed", "?")

            status_parts = []
            if signals != "0":
                status_parts.append(f"{signals} signal(s)")
            if holds != "0":
                status_parts.append(f"{holds} hold(s)")
            if errors != "0":
                status_parts.append(f"{errors} error(s)")

            summary = ", ".join(status_parts) if status_parts else "no activity"
            print(f"  {timestamp}  Done in {elapsed} — {summary}")
            return

        if message.startswith("[skip]"):
            reason = message.replace("[skip] ", "")
            print(f"  {timestamp}  Skipped: {reason}")
            return

        if message.startswith("[signal]"):
            detail = message.replace("[signal] ", "")
            print(f"  {timestamp}  ** SIGNAL ** {detail}")
            return

        if message.startswith("[hold]"):
            detail = message.replace("[hold] ", "")
            print(f"  {timestamp}  {detail}")
            return

        if message.startswith("[paper]"):
            detail = message.replace("[paper] ", "")
            print(f"  {timestamp}  [PAPER] {detail}")
            return

        if message.startswith("[portfolio]"):
            detail = message.replace("[portfolio] ", "")
            print(f"  {timestamp}  [PORTFOLIO] {detail}")
            return

        if message.startswith("[risk]"):
            detail = message.replace("[risk] ", "")
            print(f"  {timestamp}  [RISK] {detail}")
            return

        if message.startswith("[dup]"):
            detail = message.replace("[dup] ", "")
            print(f"  {timestamp}  (duplicate) {detail}")
            return

        if message.startswith("[error]"):
            detail = message.replace("[error] ", "")
            print(f"  {timestamp}  ERROR: {detail}")
            return

        # Fallback
        print(f"  {timestamp}  {message}")
