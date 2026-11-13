"""Two diagrams that explain the technology: the whole pipeline, and how the Board's PDFs are read.

    .venv/bin/python scripts/tech_diagrams.py

Writes docs/charts/5_pipeline_and_tools.png and docs/charts/6_reading_the_reports.png.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "docs" / "charts"
NAVY, BLUE, PALE, GREY, TOOL = "#1f3b57", "#2e75b6", "#eaf2fb", "#6b7280", "#b26b00"
AMBER, PALE_AMBER, GREEN, PALE_GREEN = "#b26b00", "#fdf3e1", "#2e7d32", "#e8f5e9"


def box(ax, x, y, w, h, title, sub="", tool="", fill=PALE, edge=BLUE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fill, ec=edge, lw=1.4))
    lines = [(title, 9.6, NAVY, "bold")] + [(s, 8.2, GREY, "normal") for s in sub.split("\n") if s] + \
            [(t, 8.2, TOOL, "bold") for t in tool.split("\n") if t]
    step = 0.21
    top = y + h / 2 + step * (len(lines) - 1) / 2
    for i, (text, size, colour, weight) in enumerate(lines):
        ax.text(x + w / 2, top - i * step, text, ha="center", va="center", fontsize=size, color=colour, weight=weight)


def arrow(ax, a, b, colour=BLUE, style="-|>"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=13, lw=1.4, color=colour))


def pipeline():
    fig, ax = plt.subplots(figsize=(12, 5.2))
    ax.set_xlim(-0.08, 12.12); ax.set_ylim(0, 5.2); ax.axis("off")
    w, h = 2.28, 1.45
    top = [("1. Board website", "monthly reports\nlisted as links", ""),
           ("2. Download", "find each report's link,\nsave it, fingerprint it", "Python (urllib)"),
           ("3. Read the PDFs", "pull the numbers out,\ntwo ways, then compare", "pdftotext · pdfplumber\nTesseract OCR"),
           ("4. Clean tables", "one row per area\nper month", "CSV files, Python"),
           ("5. Features", "inputs for the models,\nonly using past figures", "Python")]
    bottom = [("6. Models and backtest", "9 methods, 43 months,\ntwo months ahead", "statsmodels · scikit-learn\nXGBoost"),
              ("7. Experiment record", "every run, its settings,\nscores, charts, model", "MLflow (tracking)"),
              ("8. Model registry", "which version is in\nproduction, and why", "MLflow (registry)"),
              ("9. Monthly monitoring", "check data, score, alerts,\nChallenger check, forecast", "Python → CSV, report"),
              ("10. Dashboard", "what the team\nlooks at", "Streamlit · Altair")]
    xs = [0.02 + i * 2.43 for i in range(5)]
    for x, (t, s, tool) in zip(xs, top):
        box(ax, x, 2.95, w, h, t, s, tool)
    for x, (t, s, tool) in zip(xs, bottom):
        box(ax, x, 0.55, w, h, t, s, tool)
    for i in range(4):
        arrow(ax, (xs[i] + w, 2.95 + h / 2), (xs[i + 1], 2.95 + h / 2))
        arrow(ax, (xs[i] + w, 0.55 + h / 2), (xs[i + 1], 0.55 + h / 2))
    arrow(ax, (xs[4] + w / 2, 2.95), (xs[0] + w / 2, 0.55 + h), colour=BLUE)
    ax.text(6, 5.0, "Week 4: the whole pipeline, and the tool used at each stage", ha="center", fontsize=13, color=NAVY, weight="bold")
    ax.text(6, 4.68, "Tools in orange. Everything runs on this computer; the code and results are on GitHub.", ha="center", fontsize=9, color=GREY)
    fig.savefig(OUT / "5_pipeline_and_tools.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def reading():
    fig, ax = plt.subplots(figsize=(12, 7.0))
    ax.set_xlim(0, 12); ax.set_ylim(0, 7.0); ax.axis("off")
    w, h = 2.05, 1.3
    # lane 1: monthly release
    ax.text(0.1, 6.2, "Monthly release (2 pages, the figure we forecast)", fontsize=10.5, color=NAVY, weight="bold")
    box(ax, 0.1, 4.2, 1.7, h, "The PDF", "page 1: a table\nof 20 areas")
    box(ax, 2.35, 4.95, w, 1.0, "Reader A", "copies the page as text,\nkeeping its layout", "pdftotext")
    box(ax, 2.35, 3.55, w, 1.0, "Reader B", "lists every word with\nits place on the page", "pdfplumber")
    box(ax, 4.95, 4.2, w, h, "Compare", "every number must\nbe identical in A and B", fill=PALE_GREEN, edge=GREEN)
    box(ax, 7.55, 4.2, w, h, "Add-up checks", "areas → county → state,\nwithin $10", fill=PALE_GREEN, edge=GREEN)
    box(ax, 9.85, 4.2, 2.1, h, "Clean table", "monthly win,\n20 areas", "monthly_win.csv")
    arrow(ax, (1.8, 4.85), (2.35, 5.45)); arrow(ax, (1.8, 4.85), (2.35, 4.05))
    arrow(ax, (2.35 + w, 5.45), (4.95, 4.95)); arrow(ax, (2.35 + w, 4.05), (4.95, 4.75))
    arrow(ax, (4.95 + w, 4.85), (7.55, 4.85)); arrow(ax, (7.55 + w, 4.85), (9.85, 4.85))
    # OCR branch
    box(ax, 4.95, 2.45, w + 0.6, 0.85, "No text? (January 2025)", "the page is a picture: turn it into an\nimage, then read the letters from it", "pdftoppm + Tesseract OCR",
        fill=PALE_AMBER, edge=AMBER)
    arrow(ax, (1.0, 4.2), (4.95, 2.85), colour=AMBER)
    arrow(ax, (4.95 + w + 0.6, 2.9), (7.55 + w / 2, 4.2), colour=AMBER)
    # lane 2: monthly revenue report
    ax.text(0.1, 1.95, "Monthly Revenue Report (about 48 pages: games, tables, machines, hold)", fontsize=10.5, color=NAVY, weight="bold")
    box(ax, 0.1, 0.25, 1.7, h, "The PDF", "a detail page\nper area")
    box(ax, 2.35, 0.25, w, h, "Read every page", "as text, keeping\nthe layout", "pdftotext")
    box(ax, 4.95, 0.25, w, h, "Find the right page", "its 'Total Gaming' must\nequal the monthly release", fill=PALE_GREEN, edge=GREEN)
    box(ax, 7.55, 0.25, w, h, "Read and check", "game lines must add\nup to their totals", fill=PALE_GREEN, edge=GREEN)
    box(ax, 9.85, 0.25, 2.1, h, "Clean tables", "", "game_types_monthly.csv\ncapacity_hold_monthly.csv")
    for a, b in [(1.8, 2.35), (2.35 + w, 4.95), (4.95 + w, 7.55), (7.55 + w, 9.85)]:
        arrow(ax, (a, 0.9), (b, 0.9))
    ax.text(6, 6.9, "How the Board's PDFs become checked tables", ha="center", fontsize=13, color=NAVY, weight="bold")
    ax.text(6, 6.6, "Green: the checks that prove the numbers were read correctly. Tools in orange.", ha="center", fontsize=9, color=GREY)
    fig.savefig(OUT / "6_reading_the_reports.png", dpi=170, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    pipeline()
    reading()
    print("written: 5_pipeline_and_tools.png, 6_reading_the_reports.png")
