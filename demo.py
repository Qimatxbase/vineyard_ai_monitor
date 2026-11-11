"""Public-demo entry point: python -m streamlit run demo.py."""
import os

os.environ["VINEYARD_PUBLIC_DEMO"] = "1"

from app import main


if __name__ == "__main__":
    main()
