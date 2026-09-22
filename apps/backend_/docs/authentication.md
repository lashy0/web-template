# Production authentication

The backend authenticates browser requests with Ory Kratos and resolves every
Kratos identity to a local `User`. Authentication is wired by
`app.server.authentication.KratosAuthenticationMiddleware` in the
`ApplicationCore` composition root.

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
5. Places the local `User` object in `scope["user"]` for guards and request
   handlers.

Missing or invalid authentication, an unprovisioned identity, an inactive
local user, and an archived user result in HTTP 401. Kratos connectivity
failures result in HTTP 503. Authorization is handled separately by
`requires_permission(...)`; an authenticated user without the required exact
permission receives HTTP 403.

## Public routes

OpenAPI/Scalar routes under `/schema` are public. The current-user endpoint is
available at `/auth/me`. The health endpoint is also public and reports database
and Kratos readiness.

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
