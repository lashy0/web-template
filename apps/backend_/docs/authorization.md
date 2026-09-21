# Permission authorization

The backend authorizes endpoints with exact, namespaced permissions. A
permission is the stable contract between an endpoint, which requires it, and
an application policy, which grants it to roles. There are no wildcards,
parent namespaces, or implicit administrator access: a role can reach an
endpoint only when the application policy assigns that exact permission name.

## How the system works

- **Declarations belong to the owning domain.** Each domain defines its
  permission vocabulary in `app/domain/<domain>/permissions.py` as a
  `StrEnum` of `<domain>.<action>` values (for example, `quality.inspect`).

- **Endpoints require permissions.** Handlers declare
  `guards=[requires_permission(...)]`, one guard per required permission:

  ```python
  from app.domain.quality.permissions import QualityPermission
  from app.lib.authorization import requires_permission

  @get(
      path="/lots",
      guards=[requires_permission(QualityPermission.INSPECT)],
  )
  async def inspect_lot() -> ...:
      ...
  ```

- **Policies grant permissions to roles.** A `PermissionPolicy` is an
  immutable mapping from role name to a set of exact permission names. The
  production policy is composed explicitly in `app/server/authorization.py`
  and installed by `ApplicationCore.on_app_init` into
  `app.state["authorization_policy"]`.

- **Guards enforce both sides.** `requires_permission` comes from the
  domain-neutral `app.lib.authorization` package. It acts on the trusted
  authenticated principal that authentication middleware places in the ASGI
  scope; it never trusts role or permission claims from headers, query
  parameters, or request bodies. A missing or invalid principal returns
  HTTP 401; a valid principal without the exact permission returns HTTP 403.
  Multiple guards are cumulative: every requirement must pass before the
  handler or its dependencies run.

`app.lib.authorization` contains only the generic primitives: the immutable
`PermissionPolicy`, exact lookup helpers (`has_permission`,
`has_permission_in`, `permissions_for_role`), and the native Litestar guard.
It imports no domain code, so any domain can rely on it. Policy construction
copies and freezes all input mappings and grant sets.

The guard resolves the policy from the current application's state on every
request, so separate applications can use different immutable policies. A
missing policy grants nothing; a configured policy of the wrong type is an
application configuration error.

This backend does not yet wire production authentication middleware. Until
that prerequisite is installed, protected requests without an injected
principal correctly return 401; the future authentication layer validates the
session before populating the trusted principal.

## Adding permissions for a new domain

1. **Declare the vocabulary** in the domain package:

   ```python
   # app/domain/quality/permissions.py
   from enum import StrEnum

   class QualityPermission(StrEnum):
       INSPECT = "quality.inspect"
   ```

2. **Require it on handlers** with the native guard, as shown above.

3. **Grant it explicitly** by extending `create_authorization_policy()` in
   `app/server/authorization.py`: add the exact permission name to the
   role's grant set, for example `UserRole.ADMINISTRATOR:
   {QualityPermission.INSPECT}`. Until the policy assigns the exact name, no
   role can reach the endpoint.