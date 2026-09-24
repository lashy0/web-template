from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypeVar, cast
from uuid import UUID

import anyio
import ory_kratos_client as kratos
from anyio.to_thread import run_sync
from ory_kratos_client.api.identity_api import IdentityApi
from ory_kratos_client.api.metadata_api import MetadataApi
from ory_kratos_client.exceptions import ApiException
from ory_kratos_client.models.identity import Identity as SDKIdentity

from app.lib.kratos.exceptions import (
    KratosError,
    KratosIdentityAlreadyExistsError,
    KratosIdentityNotFoundError,
    KratosInvalidSessionError,
    KratosUnavailableError,
)
from app.lib.kratos.schemas import KratosIdentity

T = TypeVar("T")


def _to_identity(value: SDKIdentity) -> KratosIdentity:
    raw_traits = cast("object", value.traits)

    if not isinstance(raw_traits, dict):
        raise KratosUnavailableError(detail="Kratos identity contains invalid traits")

    traits = cast("dict[str, Any]", raw_traits)

    login = traits.get("login")

    if not isinstance(login, str):
        raise KratosUnavailableError(detail="Kratos identity does not contain a valid login")

    raw_metadata = cast("object", value.metadata_admin)

    metadata: dict[str, Any] | None

    if raw_metadata is None:
        metadata = None
    elif isinstance(raw_metadata, dict):
        metadata = cast("dict[str, Any]", raw_metadata)
    else:
        raise KratosUnavailableError(detail="Kratos identity contains invalid admin metadata")

    return KratosIdentity(
        id=UUID(str(value.id)),
        login=login,
        is_active=value.state == "active",
        metadata=metadata,
    )


class _SDKClient:
    """Async wrapper around the synchronous Kratos SDK."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float,
        concurrency: int,
    ) -> None:
        configuration = kratos.Configuration(
            host=base_url.rstrip("/"),
            retries=0,
        )

        self.api_client = kratos.ApiClient(configuration)
        self.timeout = timeout
        self.limiter = anyio.CapacityLimiter(concurrency)

    async def call(
        self,
        operation: Callable[[], T],
        *,
        invalid_session: bool = False,
    ) -> T:
        try:
            async with self.limiter:
                return await run_sync(operation)

        except ApiException as exc:
            status = cast("int | None", exc.status)

            if invalid_session and status in {401, 403}:
                raise KratosInvalidSessionError(
                    detail="Kratos session is invalid or expired",
                ) from exc

            if status == 404:
                raise KratosIdentityNotFoundError(detail="Identity was not found") from exc

            if status == 409:
                raise KratosIdentityAlreadyExistsError(detail="Identity already exists") from exc

            raise KratosUnavailableError(detail="Kratos request failed") from exc

        except (OSError, TimeoutError) as exc:
            raise KratosUnavailableError(detail="Kratos request failed") from exc

        except Exception as exc:
            # The generated client wraps DNS/connectivity failures in urllib3
            # exceptions (for example MaxRetryError), not OSError.
            raise KratosUnavailableError(detail="Kratos request failed") from exc


class KratosClient:
    """Kratos Admin API client for application user management."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10.0,
        concurrency: int = 4,
    ) -> None:
        client = _SDKClient(
            base_url=base_url,
            timeout=timeout,
            concurrency=concurrency,
        )

        self._client = client
        self._identities = IdentityApi(client.api_client)
        self._metadata = MetadataApi(client.api_client)

    async def is_ready(self) -> bool:
        """Return whether the Kratos Admin API reports readiness."""
        try:
            await self._client.call(lambda: self._metadata.is_ready(_request_timeout=self._client.timeout))
        except KratosError:
            return False

        return True

    async def create_identity(
        self,
        *,
        user_id: UUID,
        login: str,
        password: str,
        is_active: bool = True,
        provisioning_kind: Literal[
            "standard",
            "bootstrap",
        ] = "standard",
    ) -> KratosIdentity:
        credentials = kratos.IdentityWithCredentials(
            password=kratos.IdentityWithCredentialsPassword(
                config=kratos.IdentityWithCredentialsPasswordConfig(
                    password=password,
                )
            )
        )

        body = kratos.CreateIdentityBody(
            schema_id="default",
            external_id=str(user_id),
            state="active" if is_active else "inactive",
            traits={
                "login": login,
            },
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

        identity = await self._client.call(
            lambda: self._identities.create_identity(
                create_identity_body=body,
                _request_timeout=self._client.timeout,
            )
        )

        return _to_identity(identity)

    async def get_identity(
        self,
        identity_id: UUID,
    ) -> KratosIdentity:
        return _to_identity(await self._get_identity(identity_id))

    async def get_identity_by_user_id(
        self,
        user_id: UUID,
    ) -> KratosIdentity:
        identity = await self._client.call(
            lambda: self._identities.get_identity_by_external_id(
                external_id=str(user_id),
                _request_timeout=self._client.timeout,
            )
        )

        return _to_identity(identity)

    async def update_login(
        self,
        identity_id: UUID,
        *,
        login: str,
    ) -> KratosIdentity:
        current = await self._get_identity(identity_id)

        traits = current.traits

        if not isinstance(traits, dict):
            raise KratosUnavailableError(detail="Kratos identity contains invalid traits")

        current.traits = {
            **traits,
            "login": login,
        }

        return _to_identity(await self._update_identity(current))

    async def set_password(
        self,
        identity_id: UUID,
        *,
        password: str,
    ) -> None:
        current = await self._get_identity(identity_id)

        credentials = kratos.IdentityWithCredentials(
            password=kratos.IdentityWithCredentialsPassword(
                config=kratos.IdentityWithCredentialsPasswordConfig(
                    password=password,
                )
            )
        )

        await self._update_identity(
            current,
            credentials=credentials,
        )

    async def set_active(
        self,
        identity_id: UUID,
        *,
        is_active: bool,
    ) -> KratosIdentity:
        current = await self._get_identity(identity_id)

        current.state = "active" if is_active else "inactive"

        return _to_identity(await self._update_identity(current))

    async def revoke_all_sessions(
        self,
        identity_id: UUID,
    ) -> None:
        try:
            await self._client.call(
                lambda: self._identities.delete_identity_sessions(
                    id=str(identity_id),
                    _request_timeout=self._client.timeout,
                )
            )

        except KratosIdentityNotFoundError:
            # Kratos may return 404 when there are no sessions.
            return

    async def delete_identity(
        self,
        identity_id: UUID,
    ) -> None:
        try:
            await self._client.call(
                lambda: self._identities.delete_identity(
                    id=str(identity_id),
                    _request_timeout=self._client.timeout,
                )
            )

        except KratosIdentityNotFoundError:
            # Makes compensation/retry idempotent.
            return

    async def _get_identity(
        self,
        identity_id: UUID,
    ) -> SDKIdentity:
        return await self._client.call(
            lambda: self._identities.get_identity(
                id=str(identity_id),
                _request_timeout=self._client.timeout,
            )
        )

    async def _update_identity(
        self,
        current: SDKIdentity,
        *,
        credentials: kratos.IdentityWithCredentials | None = None,
    ) -> SDKIdentity:
        if current.state is None or not isinstance(current.traits, dict):
            raise KratosUnavailableError(detail="Kratos returned an incomplete identity")

        traits = cast("dict[str, Any]", current.traits)

        body = kratos.UpdateIdentityBody(
            schema_id=current.schema_id,
            state=current.state,
            traits=traits,
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
