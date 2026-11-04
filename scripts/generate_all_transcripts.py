"""Master Transcript Generation Pipeline for Ola Domain Support Agent.

Track: Business Operations / Customer Support (Ola)
Generates verified transcripts for all 16 tasks by delegating to the master verification runner.
"""

import os
import sys

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.run_all import main as generate_all


if __name__ == "__main__":
    generate_all()
