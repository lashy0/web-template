class AuthError(Exception):
    """Base exception for authentication and authorization errors."""


class AuthenticationError(AuthError):
    """Base exception for authentication failures."""


class InvalidSessionError(AuthenticationError):
    """The authentication session is missing, invalid, or expired."""


class AuthorizationError(AuthError):
    """Base exception for authorization failures."""


class ForbiddenError(AuthorizationError):
    """The authenticated principal lacks the required permission."""


class IdentityProviderError(AuthError):
    """Base exception for identity provider failures."""


class IdentityNotFoundError(IdentityProviderError):
    """The requested identity does not exist."""


class IdentityAlreadyExistsError(IdentityProviderError):
    """An identity with the same identifier already exists."""


class IdentityProviderUnavailableError(IdentityProviderError):
    """The identity provider is temporarily unavailable."""


class UserProvisioningError(AuthError):
    """A user could not be provisioned consistently across its backing systems."""


class AccountDisabledError(AuthenticationError):
    """The authenticated identity is inactive."""


class UserNotProvisionedError(AuthenticationError):
    """The authenticated identity has no local user projection."""
