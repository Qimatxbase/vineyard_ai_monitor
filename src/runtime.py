"""Runtime mode shared by the local workspace and isolated public demo."""
import os


def is_public_demo() -> bool:
    return os.environ.get("VINEYARD_PUBLIC_DEMO") == "1"
