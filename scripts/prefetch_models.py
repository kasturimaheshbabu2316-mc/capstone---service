"""One-time Model Prefetch Script for Ola Domain Support Intelligence System.

Track: Business Operations / Customer Support (Ola)
Downloads 'sentence-transformers/all-MiniLM-L6-v2' into the local Hugging Face cache.
Exits 0 with a clear warning on network failure so offline setup environments do not break.
"""

from __future__ import annotations

import os
import sys

MODEL_NAME = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def prefetch() -> int:
    """Pre-downloads the embedding model into local cache."""
    print("=" * 80)
    print("OLA SUPPORT INTELLIGENCE — ONE-TIME MODEL PREFETCH")
    print("=" * 80)
    print(f"[*] Target model: {MODEL_NAME}")
    print("[*] Downloading / verifying model in Hugging Face local cache...")

    try:
        from sentence_transformers import SentenceTransformer

        # Load from Hugging Face hub (requires internet if not already cached)
        model = SentenceTransformer(MODEL_NAME)
        print(f"[+] Successfully loaded and cached model: {model}")
        print("[+] One-time prefetch completed successfully.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(
            f"[!] WARNING: Failed to download model '{MODEL_NAME}': {exc}\n"
            "    If you already have the model cached or are working in an air-gapped environment,\n"
            "    the application may still run using local cached weights.",
            file=sys.stderr,
        )
        return 0


if __name__ == "__main__":
    sys.exit(prefetch())
