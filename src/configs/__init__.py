"""Configuration package.

This used to call load_dotenv() as an import side effect. Reading .env is now
owned by Settings itself (env_file in src/configs/settings.py), so importing
this package no longer does anything on its own.
"""
