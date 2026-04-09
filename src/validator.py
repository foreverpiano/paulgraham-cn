import json
import re
from pathlib import Path
from src.config import PARSED_DIR, TRANSLATED_DIR, INDEX_FILE, DIST_DIR


def validate_translation(slug: str) -> dict:
    """Validate a single translated article against its source (4-layer check)."""
    parsed_path = PARSED_DIR / f"{slug}.json"
    translated_path = TRANSLATED_DIR / f"{slug}.json"

    if not parsed_path.exists():
        return {"slug": slug, "status": "missing_source"}
    if not translated_path.exists():
        return {"slug": slug, "status": "not_translated"}

    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    translated = json.loads(translated_path.read_text(encoding="utf-8"))

    issues = []

    # Layer 1: Paragraph count
    src_para = len(parsed.get("segments", []))
    tgt_para = len(translated.get("segments", []))
    if src_para != tgt_para:
        issues.append(f"paragraph_count_mismatch: source={src_para}, translated={tgt_para}")

    # Layer 2: Footnote count and IDs
    src_fn = len(parsed.get("footnotes", []))
    tgt_fn = len(translated.get("footnotes", []))
    if src_fn != tgt_fn:
        issues.append(f"footnote_count_mismatch: source={src_fn}, translated={tgt_fn}")

    src_fn_ids = {fn["id"] for fn in parsed.get("footnotes", [])}
    tgt_fn_ids = {fn["id"] for fn in translated.get("footnotes", [])}
    if src_fn_ids != tgt_fn_ids:
        missing = src_fn_ids - tgt_fn_ids
        if missing:
            issues.append(f"footnote_ids_missing: {missing}")

    # Layer 3: Footnote ref count consistency
    src_fn_refs = parsed.get("footnote_ref_count", 0)
    tgt_fn_refs = translated.get("footnote_ref_count", 0)
    if src_fn_refs != tgt_fn_refs:
        issues.append(f"footnote_ref_count_mismatch: source={src_fn_refs}, translated={tgt_fn_refs}")

    # Layer 4: Placeholder preservation check
    # Check that FNREF and LINK placeholders are preserved in translated segments
    for i, seg in enumerate(translated.get("segments", [])):
        text_zh = seg.get("text_zh", "")
        text_orig = seg.get("text_original", "")

        # Check placeholder preservation (count-based, blocking)
        src_fnref_count = len(re.findall(r'\{\{FNREF:\d+\}\}', text_orig))
        tgt_fnref_count = len(re.findall(r'\{\{FNREF:\d+\}\}', text_zh))
        if src_fnref_count != tgt_fnref_count:
            issues.append(f"para_{i}_fnref_count: source={src_fnref_count}, translated={tgt_fnref_count}")

        src_link_count = len(re.findall(r'\{\{LINK:[^}]+\}\}', text_orig))
        tgt_link_count = len(re.findall(r'\{\{LINK:[^}]+\}\}', text_zh))
        if src_link_count != tgt_link_count:
            issues.append(f"para_{i}_link_count: source={src_link_count}, translated={tgt_link_count}")

    # Check slug preserved
    if translated.get("slug") != parsed.get("slug"):
        issues.append(f"slug_modified")

    # Check cross_page_notes full consistency
    p_cpn = parsed.get("cross_page_notes")
    t_cpn = translated.get("cross_page_notes")
    if p_cpn and not t_cpn:
        issues.append("cross_page_notes_missing_in_translated")
    if p_cpn and t_cpn:
        if p_cpn.get("notes_page_slug") != t_cpn.get("notes_page_slug"):
            issues.append("cross_page_notes_slug_mismatch")
        if p_cpn.get("ref_numbers") != t_cpn.get("ref_numbers"):
            issues.append("cross_page_notes_ref_numbers_mismatch")
        if p_cpn.get("ref_count") != t_cpn.get("ref_count"):
            issues.append("cross_page_notes_ref_count_mismatch")

    # Check is_notes_page consistency (treat missing/None as False)
    if bool(parsed.get("is_notes_page")) != bool(translated.get("is_notes_page")):
        issues.append("is_notes_page_mismatch")

    return {
        "slug": slug,
        "status": "pass" if not issues else "issues",
        "issues": issues,
    }


def validate_all() -> dict:
    if not INDEX_FILE.exists():
        print("Error: index.json not found")
        return {}

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    results = {"pass": 0, "issues": 0, "not_translated": 0, "missing_source": 0, "details": []}

    for entry in index:
        result = validate_translation(entry["slug"])
        results["details"].append(result)
        results[result["status"]] = results.get(result["status"], 0) + 1

    print(f"Validation: {results['pass']} pass, {results['issues']} issues, "
          f"{results['not_translated']} not translated, {results['missing_source']} missing source")

    if results["issues"] > 0:
        print("\nArticles with issues:")
        for r in results["details"]:
            if r["status"] == "issues":
                for issue in r["issues"][:3]:
                    print(f"  {r['slug']}: {issue}")

    return results


def check_links() -> dict:
    """Check all internal links in the generated site, including anchors."""
    if not DIST_DIR.exists():
        print("Error: dist/ not found. Run generator first.")
        return {}

    from bs4 import BeautifulSoup

    html_files = list(DIST_DIR.rglob("*.html"))

    # Build maps
    file_anchors = {}
    existing_files = {}
    for html_file in html_files:
        rel = str(html_file.relative_to(DIST_DIR))
        existing_files[rel] = html_file
        soup = BeautifulSoup(html_file.read_text(encoding="utf-8"), "lxml")
        anchors = set()
        for el in soup.find_all(id=True):
            anchors.add(el["id"])
        for el in soup.find_all("a", attrs={"name": True}):
            anchors.add(el["name"])
        file_anchors[rel] = anchors

    broken = []
    total_links = 0
    cross_article_links = 0

    for html_file in html_files:
        rel = str(html_file.relative_to(DIST_DIR))
        soup = BeautifulSoup(html_file.read_text(encoding="utf-8"), "lxml")

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") or href.startswith("mailto:"):
                continue

            total_links += 1

            if "#" in href:
                file_part, anchor_part = href.split("#", 1)
            else:
                file_part = href
                anchor_part = ""

            if file_part:
                resolved = (html_file.parent / file_part).resolve()
                try:
                    target_path = str(resolved.relative_to(DIST_DIR.resolve()))
                except ValueError:
                    broken.append({"source": rel, "href": href, "issue": f"resolves_outside_dist"})
                    continue
            else:
                target_path = rel

            target_path = target_path.replace("\\", "/")

            if "articles/" in href and file_part:
                cross_article_links += 1

            if file_part and target_path not in existing_files:
                broken.append({"source": rel, "href": href, "issue": f"file_not_found: {target_path}"})
                continue

            if anchor_part and target_path in file_anchors:
                if anchor_part not in file_anchors[target_path]:
                    broken.append({"source": rel, "href": href, "issue": f"anchor_not_found: #{anchor_part}"})

    print(f"Link check: {total_links} internal links ({cross_article_links} cross-article), {len(broken)} broken")
    if broken:
        print("\nBroken links:")
        for b in broken[:20]:
            print(f"  {b['source']} -> {b['href']} ({b['issue']})")

    return {"total": total_links, "cross_article": cross_article_links, "broken": broken}


def check_rendered_quality() -> dict:
    """Check rendered HTML for quality: no raw placeholders, correct fnrefs/links."""
    if not DIST_DIR.exists():
        return {}

    results = {"visible_fnrefs": 0, "cross_links": 0, "articles_checked": 0,
               "raw_placeholder_files": [], "backlinks": 0}

    for html_file in (DIST_DIR / "articles").glob("*.html"):
        html_text = html_file.read_text(encoding="utf-8")
        slug = html_file.stem

        results["articles_checked"] += 1

        # HARD CHECK: no raw placeholders in rendered HTML
        if "{{LINK:" in html_text or "{{FNREF:" in html_text:
            results["raw_placeholder_files"].append(slug)

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "lxml")
        content = soup.find(class_="article-content")
        if content:
            results["visible_fnrefs"] += len(content.find_all("sup"))
            results["cross_links"] += len([
                a for a in content.find_all("a", href=True)
                if a["href"].endswith(".html") and not a["href"].startswith("http")
            ])
        results["backlinks"] += len(re.findall(r'href="#fnref-f\d+n"', html_text))

    raw_count = len(results["raw_placeholder_files"])
    print(f"Rendered quality: {results['visible_fnrefs']} visible fnrefs, "
          f"{results['cross_links']} cross-links, {results['backlinks']} backlinks, "
          f"{results['articles_checked']} articles, {raw_count} with raw placeholders")
    if raw_count > 0:
        print(f"  RAW PLACEHOLDER LEAK in: {results['raw_placeholder_files'][:10]}")

    return results


if __name__ == "__main__":
    print("=== Translation Validation ===")
    validate_all()
    print("\n=== Link Check ===")
    check_links()
    print("\n=== Rendered Quality ===")
    check_rendered_quality()
