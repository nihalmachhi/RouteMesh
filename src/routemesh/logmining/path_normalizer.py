"""Low-cardinality normalization for request path labels."""

import re

UUID_SEGMENT = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def normalize_path(path: str) -> str:
    """Replace integer and UUID path segments with stable placeholders."""
    parts = path.split("?")[0].split("/")
    normalized = []
    for part in parts:
        if part.isdigit() or UUID_SEGMENT.fullmatch(part):
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized)
