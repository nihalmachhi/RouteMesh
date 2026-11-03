"""Seeded Mulberry32 random number generator shared with the browser simulator."""


class Mulberry32:
    """Generate deterministic values in [0, 1) with JavaScript-compatible math."""

    def __init__(self, seed: int) -> None:
        """Initialize the uint32 generator state."""
        self.state = seed & 0xFFFFFFFF

    def random(self) -> float:
        """Return the next Mulberry32 sample using uint32 wraparound."""
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        value = self.state
        value = ((value ^ (value >> 15)) * (value | 1)) & 0xFFFFFFFF
        value ^= (value + (((value ^ (value >> 7)) * (value | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        value &= 0xFFFFFFFF
        value ^= value >> 14
        return (value & 0xFFFFFFFF) / 4294967296
