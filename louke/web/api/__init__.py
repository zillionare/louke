"""v0.12 runtime HTTP sub-apps package.

Each module in this package exposes a self-contained Starlette application
mounted under ``/api/...`` by ``louke/web/app.py``. The sub-apps expose the
v0.12 runtime domain (``louke.runtime.*``) over JSON HTTP without modifying
the frozen v0.11 ``web/app.py`` business logic.
"""
