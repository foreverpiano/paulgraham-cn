#!/usr/bin/env python3
"""Paul Graham Chinese Site - Full pipeline entry point.

Usage:
    python main.py              # Run full pipeline: index → scrape → translate → build
    python main.py index        # Only build the page index
    python main.py scrape       # Only scrape pages (requires index)
    python main.py translate    # Only translate (requires scraped data)
    python main.py build        # Only generate the static site (requires translations)
"""
import sys
from src.config import OPENROUTER_API_KEY


def run_index():
    from src.index_builder import build_index
    return build_index()


def run_scrape():
    from src.scraper import scrape_all
    return scrape_all()


def run_translate():
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not set.")
        print("Copy .env.example to .env and add your API key.")
        sys.exit(1)
    from src.translator import translate_all
    return translate_all()


def run_build():
    from src.generator import generate_site
    return generate_site()


def run_validate():
    import sys
    from src.validator import validate_all, check_links, check_rendered_quality
    from pathlib import Path

    failures = []

    print("=== Translation Validation ===")
    v_result = validate_all()
    if v_result.get("issues", 0) > 0:
        failures.append(f"translation: {v_result['issues']} issues")

    print("\n=== Link Check ===")
    l_result = check_links()
    if l_result.get("broken"):
        failures.append(f"links: {len(l_result['broken'])} broken")

    print("\n=== Rendered Quality ===")
    r_result = check_rendered_quality()
    if r_result.get("raw_placeholder_files"):
        failures.append(f"placeholders: {len(r_result['raw_placeholder_files'])} files")
        print(f"  FAIL: raw placeholder leaks")
    else:
        print("  PASS: 0 raw placeholder leaks")

    print("\n=== Human Review Gate ===")
    review_path = Path("data/human_review.md")
    if not review_path.exists():
        failures.append("review: artifact missing")
        print("  FAIL: data/human_review.md not found")
    else:
        content = review_path.read_text()
        verdicts = len([l for l in content.split("\n") if l.startswith("**Verdict**:")])
        passes = content.count("**Verdict**: PASS")
        print(f"  Review: {verdicts} articles, {passes} PASS")
        if verdicts < 20:
            failures.append(f"review: only {verdicts} articles (need >= 20)")
            print(f"  FAIL: fewer than 20 articles reviewed")
        if "{{LINK:" in content or "{{FNREF:" in content:
            failures.append("review: contains raw placeholders")
            print(f"  FAIL: review contains raw placeholders")
        else:
            print(f"  PASS: no raw placeholders in review")

    if failures:
        print(f"\n=== VALIDATION FAILED: {', '.join(failures)} ===")
        sys.exit(1)
    else:
        print(f"\n=== ALL GATES PASSED ===")


STAGES = {
    "index": run_index,
    "scrape": run_scrape,
    "translate": run_translate,
    "build": run_build,
    "validate": run_validate,
}


def main():
    args = sys.argv[1:]

    if not args:
        # Full pipeline
        print("=" * 50)
        print("Paul Graham 中文站 - 全流程构建")
        print("=" * 50)

        print("\n[1/4] Building index...")
        run_index()

        print("\n[2/4] Scraping pages...")
        run_scrape()

        print("\n[3/4] Translating content...")
        run_translate()

        print("\n[4/4] Generating site...")
        run_build()

        print("\n" + "=" * 50)
        print("Done! Open dist/index.html to view the site.")
        print("=" * 50)
    else:
        stage = args[0]
        if stage in ("-h", "--help"):
            print(__doc__)
            return
        if stage not in STAGES:
            print(f"Unknown stage: {stage}")
            print(f"Available: {', '.join(STAGES.keys())}")
            sys.exit(1)
        STAGES[stage]()


if __name__ == "__main__":
    main()
