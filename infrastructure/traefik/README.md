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

Create the ignored Traefik environment file from its example:

```console
cp .env.example .env
```

Set `TRAEFIK_USERNAME`, `TRAEFIK_HASHED_PASSWORD`, and `ACME_EMAIL` in the
created file.

`TRAEFIK_HASHED_PASSWORD` must contain an htpasswd-compatible hash, never a
plaintext password. Wrap hashes containing `$` in single quotes so Docker
Compose preserves them literally:

```env
TRAEFIK_HASHED_PASSWORD='$apr1$...'
```

For production, set `ACME_EMAIL` to the certificate owner address.

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

Manage Traefik from the repository root:

```console
uv run --project infrastructure infra-traefik up dev
uv run --project infrastructure infra-traefik status dev
uv run --project infrastructure infra-traefik down dev
```
