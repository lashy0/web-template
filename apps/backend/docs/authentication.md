# Production authentication

The backend authenticates browser requests with Ory Kratos and resolves every
Kratos identity to a local `User`. Authentication is wired by
`app.server.authentication.KratosAuthenticationMiddleware`, a Litestar
`AbstractAuthenticationMiddleware`, in the `ApplicationCore` composition root.

## Request flow

```text
browser cookie
  -> Kratos Public API: /sessions/whoami
  -> Kratos identity.id
  -> local User.identity_id
  -> active, non-archived local User
  -> scope["user"]
  -> authorization guards
```

The middleware:

1. Reads the cookie configured by `BACKEND_KRATOS_SESSION_COOKIE` (default:
   `ory_kratos_session`).
2. Sends the original `Cookie` header to Kratos through
   `KratosSessionVerifier` and rejects missing, expired, inactive, or invalid
   sessions.
3. Gets the Kratos `identity.id` and selects the matching local user by
   `User.identity_id`.
4. Requires `User.identity_active = true` and `User.archived_at IS NULL`.
5. Places the local `User` object in `scope["user"]` (`request.user`) for
   guards and request handlers, and the Kratos identity in `scope["auth"]`
   (`request.auth`).

Missing or invalid authentication, an unprovisioned identity, an inactive
local user, and an archived user result in HTTP 401. Kratos connectivity
failures result in HTTP 503. Authorization is handled separately by
`requires_permission(...)`; an authenticated user without the required exact
permission receives HTTP 403.

## Session lifetime

A browser session ends after 8 hours without requests (`session.lifespan` in
`infrastructure/identity/kratos/kratos.yaml`). Kratos never extends a session
by itself, so `KratosSessionVerifier` does: when a verified session expires in
less than `BACKEND_KRATOS_SESSION_EXTEND_WITHIN_MINUTES` (default 420, equal to
`session.earliest_possible_extend`), it extends the session through the Kratos
Admin API. A session is thus extended at most about once an hour. A failed
extension is logged and does not fail the request.

The session cookie is not persistent: extending a session does not reissue
the cookie, and a persistent cookie would expire at the original time.

## Public routes

OpenAPI/Scalar routes under `/api/schema` are public, and so is every route
with `exclude_from_auth=True`. `OPTIONS` requests, such as CORS preflights,
are not authenticated. The current-user endpoint
is available at `/api/auth/me`. The health endpoint `/api/health` is also public
and reports database, Kratos and Hydra readiness.

## First administrator

Every backend deployment (`infra up`, `infra backend up`) runs
`app users ensure-admin` in the API container. When no active, unarchived
administrator exists, it creates the administrator `admin` (name
«Администратор») with a generated password and prints the credentials, which
the deployment shows once; otherwise it prints nothing. The password is never
stored outside Kratos.

The operator runs the other commands of `app/domain/accounts/cli.py` from the
host through `otk`, which executes the backend CLI in the running API
container, where PostgreSQL and the Kratos Admin API are reachable:

```console
uv run --project infrastructure otk users reset-password admin
uv run --project infrastructure otk users create --role operator
```

- `reset-password` replaces the password with a generated one, prints it and
  ends the user's sessions;
- `create` prompts for the password and creates any user.

The commands apply the same rules as the API and write audit entries
(`user.created`, `user.password_changed`) with the actor login `cli`.

## Local development

When the backend runs on the host while Kratos runs in the development Docker
stack, use host-published addresses instead of the Docker service name:

```env
BACKEND_KRATOS_PUBLIC_URL=http://127.0.0.1:4433
BACKEND_KRATOS_ADMIN_URL=http://127.0.0.1:4434
```

The public client is used only for browser-session verification. Admin
endpoints are used by backend provisioning and readiness checks and are never
exposed to the browser.
