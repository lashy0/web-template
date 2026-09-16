"""Keep domain persistence internals behind consumer-owned ports."""

import ast
from pathlib import Path

import pytest

_DOMAIN_ROOT = Path(__file__).parents[3] / "app" / "domains"
_PERSISTENCE_SEGMENTS = frozenset(
    {"adapter", "adapters", "model", "models", "persistence", "projection", "projections", "repository", "repositories"}
)


def _cross_domain_persistence_imports() -> list[str]:
    violations: list[str] = []
    for path in _DOMAIN_ROOT.rglob("*.py"):
        source_domain = path.relative_to(_DOMAIN_ROOT).parts[0]
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            parts = node.module.split(".")
            if len(parts) < 4 or parts[:2] != ["app", "domains"]:
                continue
            target_domain, target_path = parts[2], parts[3:]
            if source_domain != target_domain and any(
                segment in _PERSISTENCE_SEGMENTS for segment in target_path
            ):
                violations.append(f"{path.relative_to(_DOMAIN_ROOT)}:{node.lineno} -> {node.module}")
    return violations


@pytest.mark.unit
def test_domain_modules_do_not_import_other_domains_persistence_internals() -> None:
    assert _cross_domain_persistence_imports() == []
