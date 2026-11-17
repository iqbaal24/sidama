"""Deployment settings must be safe with zero environment variables.

A platform deploy that forgets to set DJANGO_DEBUG used to serve Django's debug
page with DisallowedHost, so these invariants are asserted against the real
settings module in a subprocess.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PROBE = """
import json, os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.conf import settings
print(json.dumps({
    "DEBUG": settings.DEBUG,
    "PUBLIC_ONLY": settings.PUBLIC_ONLY,
    "DEMO_AUTO_CONFIRM": settings.DEMO_AUTO_CONFIRM,
    "ALLOWED_HOSTS": settings.ALLOWED_HOSTS,
    "CSRF_TRUSTED_ORIGINS": settings.CSRF_TRUSTED_ORIGINS,
    "SECRET_KEY_LEN": len(settings.SECRET_KEY),
}))
"""

PLATFORM_VARS = ("RENDER", "RENDER_EXTERNAL_HOSTNAME", "RAILWAY_PUBLIC_DOMAIN",
                 "FLY_APP_NAME", "HEROKU_APP_DOMAIN", "SPACE_ID", "DYNO",
                 "VERCEL_URL", "DJANGO_DEBUG", "DJANGO_SECRET_KEY",
                 "DJANGO_ALLOWED_HOSTS", "SIDAMA_PUBLIC_ONLY")


def load_settings(**extra_env) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in PLATFORM_VARS}
    env.pop("DJANGO_SETTINGS_MODULE", None)
    env.update(extra_env)
    result = subprocess.run(
        [sys.executable, "-c", PROBE], cwd=BASE_DIR, env=env,
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr[-1500:])
    return json.loads(result.stdout.strip().splitlines()[-1])


class LocalDefaultsTests(unittest.TestCase):
    def test_local_runs_in_debug_with_the_full_app(self):
        settings = load_settings()
        self.assertTrue(settings["DEBUG"])
        self.assertFalse(settings["PUBLIC_ONLY"])
        self.assertIn("localhost", settings["ALLOWED_HOSTS"])


class PlatformDefaultsTests(unittest.TestCase):
    def test_render_deploy_without_env_vars_is_public_and_not_debug(self):
        settings = load_settings(RENDER="true",
                                 RENDER_EXTERNAL_HOSTNAME="sidama.onrender.com")
        self.assertFalse(settings["DEBUG"], "debug page must never be served")
        self.assertTrue(settings["PUBLIC_ONLY"])
        self.assertTrue(settings["DEMO_AUTO_CONFIRM"])
        self.assertIn("sidama.onrender.com", settings["ALLOWED_HOSTS"])
        self.assertIn("*", settings["ALLOWED_HOSTS"])
        self.assertIn("https://sidama.onrender.com", settings["CSRF_TRUSTED_ORIGINS"])
        self.assertGreaterEqual(settings["SECRET_KEY_LEN"], 40)

    def test_full_app_on_platform_keeps_strict_host_validation(self):
        settings = load_settings(RENDER="true",
                                 RENDER_EXTERNAL_HOSTNAME="sidama.onrender.com",
                                 SIDAMA_PUBLIC_ONLY="0")
        self.assertFalse(settings["DEBUG"])
        self.assertFalse(settings["PUBLIC_ONLY"])
        self.assertIn("sidama.onrender.com", settings["ALLOWED_HOSTS"])
        self.assertNotIn("*", settings["ALLOWED_HOSTS"])

    def test_hugging_face_space_is_detected(self):
        settings = load_settings(SPACE_ID="user/sidama")
        self.assertFalse(settings["DEBUG"])
        self.assertTrue(settings["PUBLIC_ONLY"])
        self.assertIn("*", settings["ALLOWED_HOSTS"])

    def test_explicit_debug_flag_still_wins(self):
        settings = load_settings(RENDER="true",
                                 RENDER_EXTERNAL_HOSTNAME="sidama.onrender.com",
                                 DJANGO_DEBUG="1")
        self.assertTrue(settings["DEBUG"])
        # The platform hostname is trusted even in debug mode.
        self.assertIn("sidama.onrender.com", settings["ALLOWED_HOSTS"])
