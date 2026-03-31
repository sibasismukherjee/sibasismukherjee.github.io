#!/usr/bin/env python3
"""update_feature_grid.py — regenerate the pgview.html feature grid and patch the version badge.

Usage:
    python3 update_feature_grid.py <features.yml> <pgview.html> <version>

Arguments:
    features.yml   Path to the pgview-features.yml file fetched from the pgview repo.
    pgview.html    Path to the portfolio pgview.html file to update in-place.
    version        Version string, e.g. "0.5.0" (without leading "v").

The script:
  1. Reads features from the YAML file.
  2. Renders each entry as a <div class="feature-card"> block.
     - If the entry has a "key" field the shortcut is rendered inside <kbd>…</kbd>.
     - All text values are HTML-escaped.
  3. Replaces the content between <!-- BEGIN FEATURE GRID --> and <!-- END FEATURE GRID -->
     in pgview.html.
  4. Patches the version badge: <span class="badge badge-teal">v…</span>.

Exit codes:
  0  Success (file updated or already up-to-date).
  1  Error (missing sentinel, YAML parse error, file not found, etc.).
"""

import html
import re
import sys

try:
    import yaml
except ImportError:
    # PyYAML not installed — fall back to a minimal parser for this simple schema
    yaml = None


def load_features(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        content = fh.read()

    if yaml is not None:
        data = yaml.safe_load(content)
        if data is None:
            raise ValueError(
                f"YAML parsed as None — file may be empty or malformed "
                f"(first 80 bytes: {content[:80]!r})"
            )
        return data.get("features", [])

    # Minimal fallback parser for the fixed schema (list of mappings under "features:")
    features = []
    current: dict | None = None
    in_features = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if stripped == "features:":
            in_features = True
            continue
        if not in_features:
            continue
        if stripped.startswith("- "):
            if current is not None:
                features.append(current)
            current = {}
            stripped = stripped[2:]
        if current is None:
            continue
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            val = val.strip().strip('"')
            current[key.strip()] = val
    if current is not None:
        features.append(current)
    return features


def render_card(feature: dict) -> str:
    name = html.escape(feature.get("name", ""))
    description = html.escape(feature.get("description", ""))
    key = feature.get("key", "")

    key_html = ""
    if key:
        key_html = f" <kbd>{html.escape(key)}</kbd>"

    return (
        "                <div class=\"feature-card\">\n"
        f"                    <h4>{name}</h4>\n"
        f"                    <p>{description}{key_html}</p>\n"
        "                </div>"
    )


def render_grid(features: list[dict]) -> str:
    cards = "\n".join(render_card(f) for f in features)
    return (
        "<!-- BEGIN FEATURE GRID -->\n"
        "            <div class=\"feature-grid\">\n"
        f"{cards}\n"
        "            </div>\n"
        "<!-- END FEATURE GRID -->"
    )


BEGIN = "<!-- BEGIN FEATURE GRID -->"
END = "<!-- END FEATURE GRID -->"


def update_html(html_path: str, features: list[dict], version: str) -> bool:
    with open(html_path, encoding="utf-8") as fh:
        original = fh.read()

    # ── Replace feature grid ─────────────────────────────────────────────────
    begin_pos = original.find(BEGIN)
    end_pos = original.find(END)
    if begin_pos == -1 or end_pos == -1:
        print(
            f"ERROR: sentinel comments not found in {html_path}.\n"
            f"  Expected: {BEGIN!r} … {END!r}",
            file=sys.stderr,
        )
        return False

    end_pos += len(END)
    new_grid = render_grid(features)
    updated = original[:begin_pos] + new_grid + original[end_pos:]

    # ── Patch version badge ──────────────────────────────────────────────────
    badge_pattern = r'<span class="badge badge-teal">v[\d.]+</span>'
    badge_replacement = f'<span class="badge badge-teal">v{version}</span>'
    updated, n_badges = re.subn(badge_pattern, badge_replacement, updated)
    if n_badges == 0:
        print("WARNING: version badge not found — skipping version patch", file=sys.stderr)

    if updated == original:
        print("No changes — already up-to-date.")
        return True

    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(updated)

    grid_changed = original[begin_pos:end_pos] != new_grid
    if grid_changed:
        print(f"Feature grid updated ({len(features)} cards).")
    if n_badges > 0 and f"v{version}" not in original:
        print(f"Version badge patched to v{version}.")
    return True


def main() -> int:
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} <features.yml> <pgview.html> <version>",
            file=sys.stderr,
        )
        return 1

    features_path, html_path, version = sys.argv[1], sys.argv[2], sys.argv[3]
    # Strip leading "v" if the caller passes "v0.5.0"
    version = version.lstrip("v")

    try:
        features = load_features(features_path)
    except FileNotFoundError:
        print(f"ERROR: features file not found: {features_path}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: failed to parse {features_path}: {exc}", file=sys.stderr)
        return 1

    if not features:
        print("ERROR: no features found in YAML — refusing to overwrite grid with empty content.", file=sys.stderr)
        return 1

    try:
        ok = update_html(html_path, features, version)
    except FileNotFoundError:
        print(f"ERROR: HTML file not found: {html_path}", file=sys.stderr)
        return 1

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
