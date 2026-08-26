from collections.abc import Callable
from typing import Any, Literal, TypeVar, cast
from uuid import UUID

import anyio
import ory_kratos_client as kratos
from ory_kratos_client.api.frontend_api import FrontendApi
from ory_kratos_client.api.identity_api import IdentityApi
from ory_kratos_client.api.metadata_api import MetadataApi
from ory_kratos_client.exceptions import ApiException
from ory_kratos_client.models.identity import Identity as KratosIdentity

from app.auth.contracts import AuthSession, Identity
from app.auth.exceptions import (
    IdentityAlreadyExistsError,
    IdentityNotFoundError,
    IdentityProviderUnavailableError,
    InvalidSessionError,
)
from app.core.config import Settings

T = TypeVar("T")


def _identity(value: KratosIdentity) -> Identity:
    traits = value.traits or {}
    return Identity(
        id=UUID(str(value.id)),
        login=str(traits["login"]),
        active=value.state == "active",
        metadata=value.metadata_admin,
    )


class _SdkClient:
    def __init__(self, *, base_url: str, timeout: float, concurrency: int) -> None:
        configuration = kratos.Configuration(host=base_url.rstrip("/"), retries=0)
        self.api_client = kratos.ApiClient(configuration)
        self.timeout = timeout
        self.limiter = anyio.CapacityLimiter(concurrency)

    async def call(self, operation: Callable[[], T]) -> T:
        try:
            async with self.limiter:
                return await anyio.to_thread.run_sync(operation)
        except ApiException as exc:
            if exc.status in {401, 403}:
                raise InvalidSessionError from exc
            if exc.status == 404:
                raise IdentityNotFoundError from exc
            if exc.status == 409:
                raise IdentityAlreadyExistsError from exc
            raise IdentityProviderUnavailableError from exc
        except (OSError, TimeoutError) as exc:
            raise IdentityProviderUnavailableError from exc


class KratosSessionVerifier:
    def __init__(self, settings: Settings) -> None:
        client = _SdkClient(
            base_url=settings.KRATOS_PUBLIC_URL,
            timeout=settings.KRATOS_PUBLIC_TIMEOUT,
            concurrency=settings.KRATOS_PUBLIC_CONCURRENCY,
        )
        self._client = client
        self._api = FrontendApi(client.api_client)

    async def verify_session(self, *, cookie_header: str) -> AuthSession:
        session = await self._client.call(
            lambda: self._api.to_session(
                cookie=cookie_header,
                _request_timeout=self._client.timeout,
            )
        )
        if session.identity is None or session.expires_at is None:
            raise IdentityProviderUnavailableError
        return AuthSession(
            id=UUID(str(session.id)),
            identity=_identity(session.identity),
            expires_at=session.expires_at,
        )


class KratosIdentityManager:
    def __init__(self, settings: Settings) -> None:
        client = _SdkClient(
            base_url=settings.KRATOS_ADMIN_URL,
            timeout=settings.KRATOS_ADMIN_TIMEOUT,
            concurrency=settings.KRATOS_ADMIN_CONCURRENCY,
        )
        self._client = client
        self._identities = IdentityApi(client.api_client)
        self._metadata = MetadataApi(client.api_client)

    async def create_identity(
        self,
        *,
        login: str,
        password: str,
        active: bool,
        user_id: UUID,
        provisioning_kind: Literal["standard", "bootstrap"] = "standard",
    ) -> Identity:
        credentials = kratos.IdentityWithCredentials(
            password=kratos.IdentityWithCredentialsPassword(
                config=kratos.IdentityWithCredentialsPasswordConfig(password=password)
            )
        )
        body = kratos.CreateIdentityBody(
            schema_id="default",
            external_id=str(user_id),
            state="active" if active else "inactive",
            traits={"login": login},
            credentials=credentials,
            metadata_admin={
                "provisioning": {
                    "owner": "backend",
                    "version": 1,
                    "kind": provisioning_kind,
                    "user_id": str(user_id),
                }
            },
        )
        result = await self._client.call(
            lambda: self._identities.create_identity(
                create_identity_body=body,
                _request_timeout=self._client.timeout,
            )
        )
        return _identity(result)

    async def get_identity_by_external_id(self, user_id: UUID) -> Identity:
        return _identity(
            await self._client.call(
                lambda: self._identities.get_identity_by_external_id(
                    external_id=str(user_id),
                    _request_timeout=self._client.timeout,
                )
            )
        )

    async def get_identity(self, identity_id: UUID) -> Identity:
        return _identity(await self._get_identity(identity_id))

    async def update_login(self, identity_id: UUID, *, login: str) -> Identity:
        current = await self._get_identity(identity_id)
        current.traits = {"login": login}
        return _identity(await self._update_identity(current))

    async def set_password(self, identity_id: UUID, *, password: str) -> None:
        current = await self._get_identity(identity_id)

        credentials = kratos.IdentityWithCredentials(
            password=kratos.IdentityWithCredentialsPassword(
                config=kratos.IdentityWithCredentialsPasswordConfig(
                    password=password
                )
            )
        )

        await self._update_identity(
            current,
            credentials=credentials,
        )

    async def set_active(self, identity_id: UUID, *, active: bool) -> Identity:
        current = await self._get_identity(identity_id)
        current.state = "active" if active else "inactive"
        return _identity(await self._update_identity(current))

    async def revoke_all_sessions(self, identity_id: UUID) -> None:
        try:
            await self._client.call(
                lambda: self._identities.delete_identity_sessions(
                    id=str(identity_id),
                    _request_timeout=self._client.timeout,
                )
            )
        except IdentityNotFoundError:
            # Kratos returns 404 when an identity has no sessions to revoke.
            # Revocation is intentionally idempotent after a successful deactivation.
            return

    async def delete_identity(self, identity_id: UUID) -> None:
        try:
            await self._client.call(
                lambda: self._identities.delete_identity(
                    id=str(identity_id),
                    _request_timeout=self._client.timeout,
                )
            )
        except IdentityNotFoundError:
            # The identity may have been removed by an earlier attempt.
            return

    async def list_identities(self, *, page_size: int) -> list[Identity]:
        result = await self._client.call(
            lambda: self._identities.list_identities(
                page_size=page_size,
                _request_timeout=self._client.timeout,
            )
        )
        return [_identity(item) for item in result]

    async def is_ready(self) -> bool:
        try:
            await self._client.call(
                lambda: self._metadata.is_ready(_request_timeout=self._client.timeout)
            )
            return True
        except IdentityProviderUnavailableError:
            return False

    async def _get_identity(self, identity_id: UUID) -> KratosIdentity:
        return await self._client.call(
            lambda: self._identities.get_identity(
                id=str(identity_id),
                _request_timeout=self._client.timeout,
            )
        )

    async def _update_identity(
        self, current: KratosIdentity,
        *,
        credentials: kratos.IdentityWithCredentials | None = None,
    ) -> KratosIdentity:
        if (
            current.schema_id is None
            or current.state is None
            or not isinstance(current.traits, dict)
        ):
            raise IdentityProviderUnavailableError
        body = kratos.UpdateIdentityBody(
            schema_id=current.schema_id,
            state=current.state,
            traits=cast(dict[str, Any], current.traits),
            external_id=current.external_id,
            metadata_admin=current.metadata_admin,
            metadata_public=current.metadata_public,
            credentials=credentials,
        )
        return await self._client.call(
            lambda: self._identities.update_identity(
                id=str(current.id),
                update_identity_body=body,
                _request_timeout=self._client.timeout,
            )
        )
