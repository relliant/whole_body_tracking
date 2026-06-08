"""Asset path helpers for whole_body_tracking."""

from pathlib import Path

# Root directory that stores robot and motion assets used by this package.
ASSET_DIR = str(Path(__file__).resolve().parent)
