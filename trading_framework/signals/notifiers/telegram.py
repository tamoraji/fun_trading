"""Telegram notifier — sends trading signals via Telegram Bot API.

Sends formatted messages to a Telegram chat. Supports both raw Signal
objects and AggregatedSignal objects (with confidence scoring).

Setup:
    1. Create a bot via @BotFather on Telegram
    2. Get the bot token
    3. Get your chat ID (message @userinfobot)
    4. Configure in JSON config or pass to constructor

Usage:
    from trading_framework.signals.notifiers.telegram import TelegramNotifier

    notifier = TelegramNotifier(bot_token="YOUR_TOKEN", chat_id="YOUR_CHAT_ID")
    notifier.send(signal)                    # Send a raw signal
    notifier.send_aggregated(agg_signal)     # Send with confidence info

Config example:
    {
        "type": "telegram",
        "bot_token": "123456:ABC-DEF...",
        "chat_id": "-1001234567890"
    }
"""
from __future__ import annotations

import json
import logging
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from ...models import Signal

logger = logging.getLogger(__name__)

# Emoji mapping for signal actions and confidence
_ACTION_EMOJI = {"BUY": "\U0001f7e2", "SELL": "\U0001f534", "HOLD": "\u26aa"}  # green, red, white circles
_CONFIDENCE_EMOJI = {"high": "\U0001f525", "medium": "\u26a1", "low": "\U0001f4a4"}  # fire, lightning, zzz


class TelegramNotifier:
    """Sends trading signals to a Telegram chat via Bot API.

    Args:
        bot_token: Telegram bot token from @BotFather.
        chat_id: Target chat/group/channel ID.
        parse_mode: Message format ('HTML' or 'MarkdownV2'). Default: HTML.
        timeout_seconds: HTTP request timeout.
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        parse_mode: str = "HTML",
        timeout_seconds: int = 10,
    ):
        if not bot_token or not chat_id:
            raise ValueError("Telegram notifier requires bot_token and chat_id.")
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.parse_mode = parse_mode
        self.timeout_seconds = timeout_seconds
        self._base_url = f"https://api.telegram.org/bot{bot_token}"

    def send(self, signal: Signal) -> bool:
        """Send a raw signal as a Telegram message.

        Returns True if sent successfully, False otherwise.
        """
        emoji = _ACTION_EMOJI.get(signal.action, "")
        text = (
            f"{emoji} <b>{signal.action}</b> {signal.symbol}\n"
            f"Price: ${signal.price:,.2f}\n"
            f"Strategy: {signal.strategy_name}\n"
            f"Reason: {signal.reason}\n"
            f"Time: {signal.timestamp.strftime('%Y-%m-%d %H:%M')}"
        )

        # Add SL/TP if present
        if "stop_loss" in signal.details:
            text += f"\nStop Loss: ${signal.details['stop_loss']:,.2f}"
        if "take_profit" in signal.details:
            text += f"\nTake Profit: ${signal.details['take_profit']:,.2f}"

        return self._send_message(text)

    def send_aggregated(self, agg_signal) -> bool:
        """Send an AggregatedSignal with confidence scoring.

        Args:
            agg_signal: An AggregatedSignal from the aggregator.

        Returns True if sent successfully.
        """
        sig = agg_signal.signal
        confidence = agg_signal.confidence.value
        conf_emoji = _CONFIDENCE_EMOJI.get(confidence, "")
        action_emoji = _ACTION_EMOJI.get(sig.action, "")

        text = (
            f"{action_emoji} <b>{sig.action}</b> {sig.symbol} "
            f"{conf_emoji} <i>{confidence.upper()} confidence</i>\n"
            f"\n"
            f"Score: {agg_signal.score:.0%}\n"
            f"Agreement: {len(agg_signal.agreeing_strategies)}/{agg_signal.total_strategies} strategies\n"
            f"Strategies: {', '.join(agg_signal.agreeing_strategies)}\n"
            f"\n"
            f"Price: ${sig.price:,.2f}\n"
            f"Time: {sig.timestamp.strftime('%Y-%m-%d %H:%M')}"
        )

        # Add SL/TP if present
        if "stop_loss" in sig.details:
            text += f"\nStop Loss: ${sig.details['stop_loss']:,.2f}"
        if "take_profit" in sig.details:
            text += f"\nTake Profit: ${sig.details['take_profit']:,.2f}"

        return self._send_message(text)

    def send_text(self, text: str) -> bool:
        """Send a plain text message."""
        return self._send_message(text)

    def _send_message(self, text: str) -> bool:
        """Send a message via the Telegram Bot API.

        Returns True if successful, False on error.
        """
        url = f"{self._base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": self.parse_mode,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            request = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.load(response)
                if not result.get("ok"):
                    logger.error("Telegram API error: %s", result.get("description", "unknown"))
                    return False
                return True
        except URLError as exc:
            logger.error("Telegram send failed: %s", exc)
            return False
        except Exception as exc:
            logger.error("Telegram unexpected error: %s", exc)
            return False
