from app.core.exceptions import (
    AppError,
    ConflictError,
    DependencyUnavailableError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
)


class AuthError(AppError):
    """Base exception for authentication and authorization errors."""

    default_message = ""


class AuthenticationError(AuthError):
    """Base exception for authentication failures."""


class InvalidSessionError(AuthenticationError, UnauthenticatedError):
    """The authentication session is missing, invalid, or expired."""

    code = "invalid_session"


class AuthorizationError(AuthError):
    """Base exception for authorization failures."""


class ForbiddenError(AuthorizationError, PermissionDeniedError):
    """The authenticated principal lacks the required permission."""

    code = "forbidden"


class IdentityProviderError(AuthError):
    """Base exception for identity provider failures."""


class IdentityNotFoundError(IdentityProviderError, NotFoundError):
    """The requested identity does not exist."""

    code = "user_not_found"


class IdentityAlreadyExistsError(IdentityProviderError, ConflictError):
    """An identity with the same identifier already exists."""

    code = "login_already_exists"


class IdentityProviderUnavailableError(IdentityProviderError, DependencyUnavailableError):
    """The identity provider is temporarily unavailable."""

    code = "identity_provider_unavailable"


class OAuthProviderError(AuthError):
    """Base exception for OAuth provider failures."""


class OAuthClientNotFoundError(OAuthProviderError, NotFoundError):
    """The requested OAuth client does not exist."""

    code = "oauth_client_not_found"


class OAuthClientAlreadyExistsError(OAuthProviderError, ConflictError):
    """An OAuth client with the same identifier already exists."""

    code = "oauth_client_already_exists"


class OAuthProviderUnavailableError(OAuthProviderError, DependencyUnavailableError):
    """The OAuth provider is temporarily unavailable."""

    code = "oauth_provider_unavailable"


class AccountDisabledError(AuthenticationError, PermissionDeniedError):
    """The authenticated identity is inactive."""

    code = "account_disabled"


class UserNotProvisionedError(AuthenticationError, PermissionDeniedError):
    """The authenticated identity has no local user projection."""

    code = "user_not_provisioned"


class InvalidMachineCredentialsError(AuthenticationError, UnauthenticatedError):
    """The supplied machine credentials are invalid."""

    code = "invalid_machine_credentials"
