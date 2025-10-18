from src.cli import Cli
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    Cli().run()
