#!/usr/bin/env python3
"""
gen_resume_pdf.py — Regenerate sibasismukherjee.pdf from sibasismukherjee-resume.html.

Self-bootstrapping: creates a local .venv on first run, installs playwright +
Chromium inside it, then re-executes itself from the venv. No manual setup needed
beyond Python 3.9+.

Usage
-----
    python scripts/gen_resume_pdf.py                  # generate, commit, push
    python scripts/gen_resume_pdf.py --dry-run        # generate only, skip git
    python scripts/gen_resume_pdf.py -m "my message"  # custom commit message
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parent.parent
HTML_SRC   = REPO_ROOT / "sibasismukherjee-resume.html"
PDF_OUT    = REPO_ROOT / "sibasismukherjee.pdf"
VENV_DIR   = REPO_ROOT / ".venv"
VENV_PY    = VENV_DIR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


# ── venv bootstrap (runs before argparse so the re-exec gets full sys.argv) ──

def bootstrap() -> None:
    """
    Ensure we're running inside .venv with playwright installed.
    If not, create the venv, install deps, and re-exec this script.
    """
    inside_venv = Path(sys.prefix).resolve() == VENV_DIR.resolve()

    if inside_venv:
        # We're in the venv — make sure playwright is present
        try:
            import playwright  # noqa: F401
        except ModuleNotFoundError:
            print("Installing playwright into .venv…")
            subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
            _install_chromium()
        return

    # Not in venv yet — create if missing
    if not VENV_PY.exists():
        print("Creating .venv…")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        print("Installing playwright into .venv…")
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "--quiet", "playwright"], check=True)
        _install_chromium()

    # Re-execute this exact script with the venv Python, forwarding all args
    os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)


def _install_chromium() -> None:
    print("Downloading Chromium for playwright (one-time)…")
    subprocess.run([str(VENV_PY), "-m", "playwright", "install", "chromium"], check=True)


# ── PDF generation ────────────────────────────────────────────────────────────

def generate_pdf() -> None:
    from playwright.sync_api import sync_playwright

    if not HTML_SRC.exists():
        sys.exit(f"ERROR: source not found: {HTML_SRC}")

    print(f"Source   → {HTML_SRC.relative_to(REPO_ROOT)}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{HTML_SRC}", wait_until="networkidle")
        page.wait_for_timeout(1500)      # let web fonts settle
        page.pdf(
            path=str(PDF_OUT),
            format="A4",
            print_background=True,       # preserve colours and backgrounds
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()

    size_kb = PDF_OUT.stat().st_size / 1024
    print(f"PDF      → {PDF_OUT.relative_to(REPO_ROOT)}  ({size_kb:.0f} KB)")


# ── git publish ───────────────────────────────────────────────────────────────

def git_publish(message: str) -> None:
    def git(*cmd: str) -> str:
        return subprocess.check_output(["git", *cmd], cwd=REPO_ROOT, text=True).strip()

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    subprocess.run(["git", "add", str(PDF_OUT)], cwd=REPO_ROOT, check=True)

    changed = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT
    ).returncode != 0

    if not changed:
        print("PDF unchanged — nothing to commit.")
        return

    subprocess.run(["git", "commit", "-m", message], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "push"], cwd=REPO_ROOT, check=True)
    print(f"Pushed   → {branch}")


# ── entrypoint ────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate PDF only; skip git commit/push",
    )
    parser.add_argument(
        "--message", "-m",
        default="resume: regenerate PDF",
        help="Git commit message  (default: 'resume: regenerate PDF')",
    )
    args = parser.parse_args()

    generate_pdf()

    if args.dry_run:
        print("Dry run — skipping git.")
    else:
        git_publish(args.message)


if __name__ == "__main__":
    bootstrap()   # may re-exec; everything below only runs inside the venv
    main()
