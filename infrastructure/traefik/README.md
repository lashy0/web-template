# Traefik

This directory contains the independent Traefik control plane for the host.
Traefik is the only public reverse proxy and owns the external
`traefik-public` Docker network. Application stacks may join this network, but
must not create or remove it.

## Files

- `docker-compose.yaml` defines the shared Traefik service, Docker provider,
  dashboard route, health check, logging limits, and external network.
- `docker-compose.dev.yaml` exposes HTTP on port 80 and enables debug logging.
- `docker-compose.prod.yaml` exposes ports 80 and 443, redirects HTTP to HTTPS,
  configures Let's Encrypt, and persists ACME state.
- `.env.example` documents Traefik-specific environment variables.
- [`scripts/`](scripts/README.md) contains the operational CLI.

## Configuration

Traefik reads configuration from two ignored environment files:

- the repository `.env` provides `BASE_DOMAIN`;
- `infrastructure/traefik/.env` provides `TRAEFIK_USERNAME`,
  `TRAEFIK_HASHED_PASSWORD`, and `ACME_EMAIL`.

Create them from their examples:

```console
cp .env.example .env
cp infrastructure/traefik/.env.example infrastructure/traefik/.env
```

`TRAEFIK_HASHED_PASSWORD` must contain an htpasswd-compatible hash, never a
plaintext password. Wrap hashes containing `$` in single quotes so Docker
Compose preserves them literally:

```env
TRAEFIK_HASHED_PASSWORD='$apr1$...'
```

For development, use `BASE_DOMAIN=localhost`. For production, use the public
base domain and set `ACME_EMAIL` to the certificate owner address.

## Development

The development configuration serves HTTP on port 80 and uses verbose common
logs. The Basic-Auth-protected dashboard is available at:

<http://traefik.localhost/dashboard/>

## Production

The production configuration:

- listens directly on host ports 80 and 443;
- redirects all HTTP traffic to HTTPS;
- obtains certificates through Let's Encrypt TLS-ALPN-01;
- stores ACME data in the `traefik-acme` named volume;
- writes structured JSON logs;
- serves the Basic-Auth-protected dashboard at
  `https://traefik.<BASE_DOMAIN>/dashboard/`.

This topology expects Traefik to terminate public traffic directly. It does not
include an upstream CDN, load balancer, TLS terminator, or second reverse proxy.

Application routes are discovered from Docker labels. For example, the backend
application publishes `api.<BASE_DOMAIN>` when its stack joins
`traefik-public`.

## Operations

Use the [Traefik deployment CLI](scripts/README.md) to start, inspect, or stop
the development and production configurations.
