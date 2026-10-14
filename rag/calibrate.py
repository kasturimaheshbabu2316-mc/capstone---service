"""Empirical Cosine Similarity Calibration Module.

Track: Business Operations / Customer Support (Ola)
Calibrates the similarity threshold between in-scope and out-of-scope customer queries.
"""

from typing import Tuple, List, Dict, Any
from rag.generate import calibrate_threshold, CALIBRATED_THRESHOLD

__all__ = ["calibrate_threshold", "CALIBRATED_THRESHOLD"]


if __name__ == "__main__":
    threshold, in_res, out_res = calibrate_threshold()
    print(f"Calibrated Threshold: {threshold}")
