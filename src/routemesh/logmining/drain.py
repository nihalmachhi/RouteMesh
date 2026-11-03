"""Small Drain-style token template miner for operational logs."""

import re
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"\"[^\"]*\"|'[^']*'|\S+")
VARIABLE_PATTERN = re.compile(r"^(?:\d+|[0-9a-fA-F-]{16,}|\d+\.\d+(?:ms|s)?)$")


@dataclass(frozen=True, slots=True)
class MinedTemplate:
    """Template returned for one log line."""

    template_id: int
    template: str
    count: int
    is_new: bool


class DrainMiner:
    """Cluster log lines by token count and stable prefixes."""

    def __init__(self, depth: int = 3, similarity: float = 0.5) -> None:
        """Set a bounded prefix depth and token similarity threshold."""
        if depth < 1 or not 0 < similarity <= 1:
            raise ValueError("depth and similarity must be positive and bounded")
        self.depth = depth
        self.similarity = similarity
        self._templates: list[list[str]] = []
        self._counts: list[int] = []

    def add(self, line: str) -> MinedTemplate:
        """Return an existing generalized template or create a new cluster."""
        tokens = TOKEN_PATTERN.findall(line.strip())
        if not tokens:
            tokens = ["<EMPTY>"]
        candidates = [
            index
            for index, template in enumerate(self._templates)
            if len(template) == len(tokens)
            and all(
                template[pos] == tokens[pos]
                for pos in range(min(self.depth, len(tokens)))
                if template[pos] != "*"
            )
        ]
        best = max(
            candidates,
            key=lambda index: (
                sum(a == b for a, b in zip(self._templates[index], tokens, strict=True))
                / len(tokens)
            ),
            default=None,
        )
        if (
            best is None
            or sum(a == b for a, b in zip(self._templates[best], tokens, strict=True)) / len(tokens)
            < self.similarity
        ):
            template = ["*" if VARIABLE_PATTERN.match(token) else token for token in tokens]
            self._templates.append(template)
            self._counts.append(1)
            index = len(self._templates) - 1
            return MinedTemplate(index, " ".join(template), 1, True)
        self._templates[best] = [
            old if old == token else "*"
            for old, token in zip(self._templates[best], tokens, strict=True)
        ]
        self._counts[best] += 1
        return MinedTemplate(best, " ".join(self._templates[best]), self._counts[best], False)

    def templates(self) -> list[MinedTemplate]:
        """Return all current templates in insertion order."""
        return [
            MinedTemplate(index, " ".join(template), self._counts[index], False)
            for index, template in enumerate(self._templates)
        ]
