"""Settings for the test suite: isolated data dir, debug on, in-memory database."""

import os
import tempfile

os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ["AQUAPIN_DATA_DIR"] = tempfile.mkdtemp(prefix="aquapin-test-")
os.environ["TELEGRAM_WEBHOOK_SECRET"] = ""
os.environ["TELEGRAM_BOT_TOKEN"] = ""

from .settings import *  # noqa: E402,F401,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
