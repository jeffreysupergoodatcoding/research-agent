"""Output adapters — convert Research Agent task outputs to consumer-specific formats.

Each adapter is a pure function. No I/O coupling between adapters.
Pulse and Fragment adapters are independent — improving one doesn't risk the other.
"""
