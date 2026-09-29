"""Find collocates for a target word in the tokenized novel.

Usage:  python -X utf8 collocates.py [target_word] [output_dir]
        (defaults: 郭靖, output/)

For each of three configurations (window with horizon 5, window with
horizon 10, and sentence-based), find_collocates from qhchina computes a
Fisher's exact test per candidate collocate. Results are filtered to:

- collocates that are not stopwords (loaded via qhchina.load_stopwords)
- collocates with at least 2 characters
- collocates with a p-value below 0.05

Each result is sorted by obs_local (descending), saved to its own CSV in
output/, and the top 20 rows are printed to the terminal.
"""

import sys
from pathlib import Path

from qhchina import load_stopwords
from qhchina.analytics.collocations import find_collocates

SENTENCES_PATH = "sentences.txt"
OUTPUT_DIR = "output"
# ASCII labels for CSV filenames, keyed by target word
TARGET_LABELS = {"郭靖": "guojing", "黄蓉": "huangrong", "小王爷": "xiaowangye",
                 "六怪": "liuguai", "师父": "shifu"}
MIN_WORD_LENGTH = 2
P_THRESHOLD = 0.05  # keep only collocates with p-value strictly below this
TOP_N = 20

RUNS = [
    {"label": "window_h5", "method": "window", "horizon": 5},
    {"label": "window_h10", "method": "window", "horizon": 10},
    {"label": "sentence", "method": "sentence", "horizon": None},
]


def load_sentences(path):
    """Read sentences.txt (one sentence per line, space-separated tokens)."""
    with open(path, encoding="utf-8") as f:
        return [line.split() for line in f if line.strip()]


def main():
    # Usage: python -X utf8 collocates.py [target_word] [output_dir]
    target = sys.argv[1] if len(sys.argv) > 1 else "郭靖"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(OUTPUT_DIR)
    label = TARGET_LABELS.get(target)
    if label is None:
        valid = "、".join(TARGET_LABELS)
        raise SystemExit(f"No filename label defined for target {target!r}; add one to TARGET_LABELS (existing: {valid})")

    sentences = load_sentences(SENTENCES_PATH)
    stopwords = load_stopwords()
    print(f"Loaded {len(sentences)} sentences and {len(stopwords)} stopwords")
    print(f"Target word: {target} | p < {P_THRESHOLD} | min length {MIN_WORD_LENGTH}")

    out_dir.mkdir(exist_ok=True)

    filters = {
        "stopwords": stopwords,
        "min_word_length": MIN_WORD_LENGTH,
        "max_p": P_THRESHOLD,  # keeps p_value <= threshold; strict < applied below
    }

    for run in RUNS:
        result = find_collocates(
            sentences,
            target,
            method=run["method"],
            horizon=run["horizon"],
            filters=filters,
            sort_by="obs_local",
            ascending=False,
        )

        # Enforce a strictly-below threshold (the built-in max_p filter is <=).
        result = result[result["p_value"] < P_THRESHOLD]
        result = result.sort_values("obs_local", ascending=False).reset_index(drop=True)

        csv_path = out_dir / f"collocates_{label}_{run['label']}.csv"
        result.to_csv(csv_path, index=False, encoding="utf-8-sig")

        method_desc = f"method={run['method']}, horizon={run['horizon']}"
        print(f"\n=== {method_desc} -> {csv_path} ===")
        print(f"{len(result)} collocates with p < {P_THRESHOLD}; top {TOP_N} by obs_local:")
        print(result.head(TOP_N).to_string(index=False))


if __name__ == "__main__":
    main()