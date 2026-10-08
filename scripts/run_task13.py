"""Task 13 Runner: 15-Query Evaluation Suite & LLM-as-Judge Benchmark."""

import os
import sys

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from eval.run_eval import run_benchmark


def run():
    print("Executing Task 13: 15-Query Evaluation Benchmark...")
    run_benchmark()


if __name__ == "__main__":
    run()
