# Traefik

This directory contains the independent Traefik control plane for the host.
Traefik is the only public reverse proxy and owns the external
`traefik-public` Docker network. Application stacks may join this network, but
must not create or remove it.

## Structure

```text
traefik/
├── .env.example               Traefik-specific environment template
├── docker-compose.yaml        Service, Docker provider, dashboard and network
├── docker-compose.dev.yaml    Development HTTP port and debug logging
├── docker-compose.prod.yaml   HTTPS, Let's Encrypt and persistent ACME state
└── README.md
```

The base Compose file contains settings shared by both environments; dev and
prod files provide the environment-specific overrides.

## Configuration

`infra init` creates the ignored `.env` from its example with the dashboard
user `admin` and a random password; the password is written in a comment
above its hash.

To change the password, replace `TRAEFIK_HASHED_PASSWORD` with another
htpasswd-compatible hash, never a plaintext password. Wrap hashes containing
`$` in single quotes so Docker Compose preserves them literally:

```env
TRAEFIK_HASHED_PASSWORD='$apr1$...'
```

For production, set `ACME_EMAIL` to the certificate owner address and
`TRAEFIK_DASHBOARD_ADDRESS` to the server's local-network address.

## Dashboard

The dashboard never shares the public entrypoints: Traefik's own API lives
under `/api`, which the application host routes to the backend. It uses
Traefik's internal `traefik` entrypoint on container port 8080, published only
on a local address, and is protected by an IP allowlist of private ranges and
Basic Auth.
Docker-published ports bypass host firewalls such as ufw, so the bind address
is what keeps the port off the public interface. Basic Auth travels over plain
HTTP inside the local network.

## Development

The development configuration serves HTTP on port 80 and uses verbose common
logs. It routes `http://${APP_HOST}` like production, with the Vite dev server
at `/`. The dashboard is available at <http://127.0.0.1:8080/dashboard/>.

## Production

The production configuration:

- listens directly on host ports 80 and 443;
- redirects all HTTP traffic to HTTPS;
- obtains certificates through Let's Encrypt TLS-ALPN-01;
- stores ACME data in the `otk-app-traefik_traefik-acme` volume;
- writes structured JSON logs;
- serves the dashboard at `http://<TRAEFIK_DASHBOARD_ADDRESS>:8080/dashboard/`.

This topology expects Traefik to terminate public traffic directly. It does not
include an upstream CDN, load balancer, TLS terminator, or second reverse proxy.

Application routes are discovered from Docker labels. All of them are on the
one host `${APP_HOST}`: the frontend at `/`, the backend at `/api`, and Ory at
`/.ory`.

## Operations

Manage Traefik from the repository root:

```console
uv run --project infrastructure infra traefik up dev
uv run --project infrastructure infra traefik status dev
uv run --project infrastructure infra traefik down dev
```
