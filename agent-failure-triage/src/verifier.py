from typing import List, Tuple


def normalize_text(text: str) -> str:
    """Remove extraneous whitespace, tabs, and case variations."""
    return " ".join(text.split()).lower()


def verify_evidence(raw_trace: str, cited_evidence: List[str]) -> Tuple[bool, List[str]]:
    """
    Deterministic zero-token evidence verifier.
    Every cited snippet must be an exact normalized substring of raw_trace.
    """
    if not cited_evidence:
        return False, ["No evidence provided."]

    raw_normalized = normalize_text(raw_trace)
    unverified: List[str] = []

    for snippet in cited_evidence:
        cleaned = snippet.strip()
        if not cleaned:
            continue
        if normalize_text(cleaned) not in raw_normalized:
            unverified.append(snippet)

    if unverified:
        return False, unverified
    return True, []
