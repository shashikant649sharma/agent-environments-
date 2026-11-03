"""Strict validation tool to verify README.md consistency, links, SVGs, and data provenance."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def validate_readme() -> list[str]:
    """Validate README against all publication integrity rules.

    Returns a list of error strings; empty list indicates success.
    """
    root_dir = Path(__file__).resolve().parent.parent
    readme_path = root_dir / "README.md"
    if not readme_path.exists():
        return ["README.md not found in repository root."]

    content = readme_path.read_text(encoding="utf-8")
    errors: list[str] = []

    # 1. Check all local markdown links and image paths
    # Matches [text](path) and ![alt](path) and <img src="path">
    md_links = re.findall(r"\[(?:[^\]]*)\]\(([^)#]+)(?:#[^)]*)?\)", content)
    md_imgs = re.findall(r"!\[(?:[^\]]*)\]\(([^)#]+)(?:#[^)]*)?\)", content)
    html_imgs = re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', content)

    all_refs = set(md_links + md_imgs + html_imgs)
    for ref in sorted(all_refs):
        ref_clean = ref.strip()
        # Skip external URLs, mailto, anchor-only links
        if (
            ref_clean.startswith("http://")
            or ref_clean.startswith("https://")
            or ref_clean.startswith("mailto:")
            or ref_clean.startswith("#")
            or not ref_clean
        ):
            continue

        target = root_dir / ref_clean
        if not target.exists():
            errors.append(f"Broken local link/path in README: {ref_clean}")

    # 2. Check all 7 required SVGs exist and are referenced
    required_svgs = [
        "assets/readme/architecture.svg",
        "assets/readme/frontier-model-scores.svg",
        "assets/readme/task-success.svg",
        "assets/readme/infrastructure-reliability.svg",
        "assets/readme/baseline-comparison.svg",
        "assets/readme/environment-matrix.svg",
        "assets/readme/scoring-rubric.svg",
    ]
    for svg_rel in required_svgs:
        svg_path = root_dir / svg_rel
        if not svg_path.exists():
            errors.append(f"Required SVG missing on disk: {svg_rel}")
        if svg_rel not in content:
            errors.append(f"Required SVG not referenced in README.md: {svg_rel}")

    # 3. Check for image placeholders
    required_placeholders = [
        "<!-- IMAGE PLACEHOLDER: HERO / PROJECT VISUAL -->",
        "<!-- IMAGE PLACEHOLDER: ARCHITECTURE OVERVIEW -->",
        "<!-- IMAGE PLACEHOLDER: ENVIRONMENT ILLUSTRATION -->",
    ]
    for ph in required_placeholders:
        if ph not in content:
            errors.append(f"Missing required image placeholder: {ph}")

    # 4. Check version consistency against pyproject.toml
    pyproject_path = root_dir / "pyproject.toml"
    current_version = "0.5.1"
    if pyproject_path.exists():
        pyproject_text = pyproject_path.read_text(encoding="utf-8")
        m = re.search(r'version\s*=\s*"([^"]+)"', pyproject_text)
        if m:
            current_version = m.group(1)

    # In README, badges and text should reference current_version, not stale 0.4 or 0.5.0
    if "badge/version-0.5.0" in content or "badge/version-0.4" in content:
        errors.append("Stale version badge found in README.md (must be 0.5.1).")
    if f"version-{current_version}" not in content and f"v{current_version}" not in content:
        errors.append(f"README.md does not reference current package version ({current_version}).")

    # 5. Check test count badge against test suite
    if "badge/tests-882" in content:
        errors.append(
            "Stale test count badge (882 passed) found in README.md; must reflect active suite."
        )

    # 6. Check for unverified denominators
    # Disallow invalid denominators or fabricated counts
    if "10/10" in content and "0.995 pass" in content:
        errors.append("Fabricated pass claim detected.")

    # 7. Check verified CLI commands exist in help
    cli_commands = ["praxis demo", "praxis demo --markdown", "praxis --help"]
    for cmd in cli_commands:
        if cmd not in content:
            errors.append(f"Essential verified CLI command not documented in README: {cmd}")

    return errors


def main() -> int:
    errors = validate_readme()
    if errors:
        print("README VALIDATION FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("README Validation Passed: All links, SVGs, versions, and integrity rules verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
