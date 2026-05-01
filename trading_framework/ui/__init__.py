"""UI layer — all user-facing interfaces.

Multiple UI options for different use cases:
- cli          — Command-line interface with argparse
- interactive  — Setup wizard with Quick Start, Presets, Advanced paths
- tui          — Live terminal dashboard (Textual)
- web          — Browser dashboard (FastAPI + Plotly)
- telegram     — Telegram bot for notifications + HITL    [planned]

All UIs consume the Service layer. No business logic here.

Dependencies: service layer only (+ UI framework dependencies).
"""
