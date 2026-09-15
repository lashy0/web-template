from app.auth.contracts import Identity as LegacyIdentity
from app.auth.principal import CurrentPrincipal as LegacyCurrentPrincipal
from app.auth.roles import Role as LegacyRole
from app.shared.security import CurrentPrincipal, Identity, Role


def test_legacy_security_imports_reference_the_shared_canonical_types() -> None:
    assert LegacyRole is Role
    assert LegacyCurrentPrincipal is CurrentPrincipal
    assert LegacyIdentity is Identity
