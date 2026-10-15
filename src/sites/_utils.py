"""Small helpers shared by the sites."""


def dedupe(results):
    """Drop duplicate search results (same URL)."""
    seen, out = set(), []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            out.append(r)
    return out
