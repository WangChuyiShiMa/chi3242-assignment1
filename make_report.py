"""Build single-page HTML reports for the collocate tables.

Usage:  python -X utf8 make_report.py [src_dir] [dest_html]
        (defaults: output/, output/results.html)

Reads every <src_dir>/collocates_<target>_<run>.csv produced by collocates.py
and writes:

- <dest_html>                          — all targets in one page
- <dest_html's folder>/results_<target>.html — one page per target

Each page is self-contained (no external dependencies) with a dropdown that
switches between the tables.
"""

import html
import re
import sys
from pathlib import Path
from string import Template

import pandas as pd

OUTPUT_DIR = Path("output")
REPORT_PATH = OUTPUT_DIR / "results.html"

# Dropdown labels for the run part of the filename, in display order
RUN_LABELS = {
    "window_h5": "Window (horizon = 5)",
    "window_h10": "Window (horizon = 10)",
    "sentence": "Sentence-based",
}
RUN_ORDER = {key: i for i, key in enumerate(RUN_LABELS)}
# ASCII target label from filename -> display form for headings
TARGET_NAMES = {"guojing": "郭靖", "huangrong": "黄蓉", "xiaowangye": "小王爷",
                "liuguai": "六怪", "shifu": "师父"}

NUMERIC_COLS = {"exp_local", "obs_local", "ratio_local", "obs_global", "p_value"}


def format_cell(col, value):
    """Format a cell for display (full precision stays in the CSVs)."""
    if col in ("obs_local", "obs_global"):
        return f"{int(value)}"
    if col in ("exp_local", "ratio_local"):
        return f"{value:.2f}"
    if col == "p_value":
        return f"{value:.2e}"
    return html.escape(str(value))


def build_table(df):
    head = "".join(
        f'<th class="{"num" if col in NUMERIC_COLS else "txt"}">{html.escape(col)}</th>'
        for col in df.columns
    )
    rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            classes = []
            if col in NUMERIC_COLS:
                classes.append("num")
            if col == "obs_local":
                classes.append("obs")
            elif col == "p_value":
                classes.append("pv")
            cls = f' class="{" ".join(classes)}"' if classes else ""
            cells.append(f"<td{cls}>{format_cell(col, row[col])}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        "<table><thead><tr>" + head + "</tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


PAGE_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    margin: 0; background: #f6f3ec; color: #2b2b2b;
  }
  header { padding: 24px 32px 12px; }
  h1 { font-size: 1.45rem; margin: 0 0 4px; }
  h1 .target { color: #9e2b25; }
  h1 .src { font-size: 1rem; font-weight: 400; color: #7a7365; }
  .subtitle { margin: 0 0 14px; font-size: .88rem; color: #7a7365; }
  .controls { display: flex; align-items: center; gap: 10px; }
  .controls label { font-size: .92rem; color: #55503f; }
  select {
    font: inherit; font-size: .95rem; padding: 6px 10px;
    border: 1px solid #c9c1a9; border-radius: 6px; background: #fffdf7;
    cursor: pointer; min-width: 280px;
  }
  main { padding: 4px 32px 32px; }
  section.run { display: none; background: #fffdf7;
    border: 1px solid #ddd6c2; border-radius: 10px; overflow: hidden; }
  section.run.active { display: block; }
  .caption { margin: 0; padding: 11px 16px; font-size: .88rem; color: #6b6450;
    border-bottom: 1px solid #ece5d2; background: #fbf8ef; }
  .table-wrap { max-height: calc(100vh - 240px); min-height: 200px; overflow: auto; }
  table { border-collapse: collapse; width: 100%; font-size: .93rem; }
  th, td { padding: 6px 14px; border-bottom: 1px solid #f0e9d8; white-space: nowrap; }
  thead th { position: sticky; top: 0; z-index: 1; background: #f3edda;
    border-bottom: 2px solid #d9d1b6; text-align: left; }
  th.num, td.num { text-align: right; font-variant-numeric: tabular-nums; }
  td.obs { font-weight: 600; }
  td.pv { font-family: Consolas, Menlo, monospace; font-size: .88rem; }
  tbody tr:nth-child(even) { background: #faf6ea; }
  tbody tr:hover { background: #f2ecda; }
</style>
</head>
<body>
<header>
  <h1>Collocates of <span class="target">$heading</span>
      <span class="src">· 射雕英雄传 (一)</span></h1>
  <p class="subtitle">Fisher's exact test · p &lt; 0.05 · collocates ≥ 2 characters ·
     stopwords removed · sorted by obs_local, high → low</p>
  <div class="controls">
    <label for="run-select">Switch table:</label>
    <select id="run-select">$options</select>
  </div>
</header>
<main>
$sections
</main>
<script>
  const select = document.getElementById("run-select");
  select.addEventListener("change", () => {
    const active = select.value;
    document.querySelectorAll("section.run").forEach(s => {
      s.classList.toggle("active", s.id === active);
    });
  });
</script>
</body>
</html>
""")


def discover_csvs(base_dir):
    """Find all collocates_*.csv in base_dir, grouped by target (郭靖 first)."""
    files = {}
    for path in base_dir.glob("collocates_*.csv"):
        m = re.fullmatch(r"collocates_([a-z]+)_(window_h\d+|sentence)\.csv", path.name)
        if not m:
            print(f"Skipping unrecognized file: {path.name}")
            continue
        target_label, run_key = m.groups()
        files.setdefault(target_label, []).append(
            (RUN_ORDER[run_key], RUN_LABELS[run_key], path)
        )
    if not files:
        raise SystemExit(
            f"No collocates_*.csv found in {OUTPUT_DIR} — run collocates.py first"
        )
    # Targets in defined order first (郭靖, 黄蓉), then any others alphabetically
    known = [t for t in TARGET_NAMES if t in files]
    unknown = sorted(t for t in files if t not in TARGET_NAMES)
    return [(t, sorted(files[t])) for t in known + unknown]


def build_target_page(target_name, runs, show_target_in_labels):
    """Build one page: dropdown + sections for a target's runs."""
    options, sections = [], []
    for _, run_label, path in runs:
        df = pd.read_csv(path, encoding="utf-8-sig")
        run_id = f"run-{path.stem.split('_', 2)[2]}"
        active = " active" if not options else ""
        label = f"{target_name} · {run_label}" if show_target_in_labels else run_label
        options.append(
            f'<option value="{run_id}">{html.escape(label)} — {len(df)} collocates</option>'
        )
        sections.append(
            f'<section class="run{active}" id="{run_id}">'
            f'<p class="caption">{html.escape(label)} · {len(df)} collocates · '
            f'sorted by obs_local ↓</p>'
            f'<div class="table-wrap">{build_table(df)}</div>'
            f"</section>"
        )
    return options, sections


def build_page(title, heading, options, sections):
    return PAGE_TEMPLATE.substitute(
        title=title, heading=heading,
        options="".join(options), sections="".join(sections),
    )


def main():
    src_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_DIR
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else REPORT_PATH

    targets = discover_csvs(src_dir)

    all_options, all_sections = [], []
    total_rows = 0
    for target_label, runs in targets:
        target_name = TARGET_NAMES.get(target_label, target_label)

        # Build sections once: per-target page labels without the target name,
        # combined page labels with it
        options_plain, sections_plain = build_target_page(target_name, runs, show_target_in_labels=False)
        options_named, sections_named = build_target_page(target_name, runs, show_target_in_labels=True)

        # Per-target page (written next to the combined report)
        per_target_path = dest.parent / f"results_{target_label}.html"
        per_target_path.write_text(
            build_page(
                f"Collocates of {target_name} — 射雕英雄传",
                target_name, options_plain, sections_plain,
            ),
            encoding="utf-8",
        )
        n_rows = sum(len(pd.read_csv(p, encoding="utf-8-sig")) for *_, p in runs)
        total_rows += n_rows
        print(f"Wrote {per_target_path} ({len(runs)} tables, {n_rows} rows for {target_name})")

        # Combined page entries: target name shown, ids prefixed to stay unique
        for (_, run_label, path), opt, sec in zip(runs, options_named, sections_named):
            all_options.append(opt.replace('value="run-', f'value="run-{target_label}-'))
            all_sections.append(sec.replace('id="run-', f'id="run-{target_label}-'))

    dest.write_text(
        build_page(
            "Collocates — 射雕英雄传", " / ".join(
                TARGET_NAMES.get(t, t) for t, _ in targets
            ),
            all_options, all_sections,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {dest} ({sum(len(r) for _, r in targets)} tables, "
          f"{total_rows} rows total)")


if __name__ == "__main__":
    main()