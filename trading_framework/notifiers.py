from __future__ import annotations

import json
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from typing import Dict, Iterable, List
from urllib.request import Request, urlopen

from .models import NotifierSettings, Signal


class Notifier(ABC):
    @abstractmethod
    def send(self, signal: Signal) -> None:
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    def send(self, signal: Signal) -> None:
        print(format_signal(signal))


class WebhookNotifier(Notifier):
    def __init__(self, url: str, timeout_seconds: int = 10, headers: Dict[str, str] | None = None):
        if not url:
            raise ValueError("Webhook notifier requires a non-empty URL.")
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.headers = headers or {}

    def send(self, signal: Signal) -> None:
        payload = {
            "symbol": signal.symbol,
            "action": signal.action,
            "price": signal.price,
            "timestamp": signal.timestamp.isoformat(),
            "strategy": signal.strategy_name,
            "reason": signal.reason,
            "details": signal.details,
        }
        request = Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **self.headers},
        )
        with urlopen(request, timeout=self.timeout_seconds):
            return None


class EmailNotifier(Notifier):
    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        recipients: Iterable[str],
        username: str = "",
        password: str = "",
        use_tls: bool = True,
        timeout_seconds: int = 10,
    ):
        recipients = [recipient for recipient in recipients if recipient]
        if not host or not sender or not recipients:
            raise ValueError("Email notifier requires host, sender, and at least one recipient.")

        self.host = host
        self.port = port
        self.sender = sender
        self.recipients = recipients
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.timeout_seconds = timeout_seconds

    def send(self, signal: Signal) -> None:
        message = EmailMessage()
        message["Subject"] = f"{signal.action} signal for {signal.symbol}"
        message["From"] = self.sender
        message["To"] = ", ".join(self.recipients)
        message.set_content(format_signal(signal))

        with smtplib.SMTP(self.host, self.port, timeout=self.timeout_seconds) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(message)


def create_notifiers(settings_list: List[NotifierSettings]) -> List[Notifier]:
    notifiers: List[Notifier] = []

    for settings in settings_list:
        if not settings.enabled:
            continue

        if settings.type == "console":
            notifiers.append(ConsoleNotifier())
            continue

        if settings.type == "webhook":
            notifiers.append(
                WebhookNotifier(
                    url=str(settings.params.get("url", "")),
                    timeout_seconds=int(settings.params.get("timeout_seconds", 10)),
                    headers=dict(settings.params.get("headers", {})),
                )
            )
            continue

        if settings.type == "email":
            raw_recipients = settings.params.get("recipients", [])
            recipients = raw_recipients if isinstance(raw_recipients, list) else [raw_recipients]
            notifiers.append(
                EmailNotifier(
                    host=str(settings.params.get("host", "")),
                    port=int(settings.params.get("port", 587)),
                    sender=str(settings.params.get("sender", "")),
                    recipients=recipients,
                    username=str(settings.params.get("username", "")),
                    password=str(settings.params.get("password", "")),
                    use_tls=bool(settings.params.get("use_tls", True)),
                    timeout_seconds=int(settings.params.get("timeout_seconds", 10)),
                )
            )
            continue

        raise ValueError(f"Unsupported notifier: {settings.type}")

    return notifiers or [ConsoleNotifier()]


def format_signal(signal: Signal) -> str:
    return (
        f"[{signal.timestamp.isoformat()}] {signal.action} {signal.symbol} at "
        f"{signal.price:.2f} via {signal.strategy_name}: {signal.reason}"
    )
