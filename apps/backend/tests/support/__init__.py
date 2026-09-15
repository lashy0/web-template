"""Shared test support: actors, recording collaborators and in-memory stores.

Tests assert on observable outcomes - returned state, stored state, recorded
audit - never on the shape of a call. Nothing here uses ``unittest.mock``, so a
renamed repository method breaks the fake at import/attribute level instead of
silently passing.
"""
