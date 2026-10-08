"""Provide a non-secret token-shaped value for modules that construct aiogram.Bot on import."""

import os


os.environ.setdefault("TOKEN", "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
