# syntax=docker/dockerfile:1

FROM node:24-alpine AS dependencies

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH

RUN corepack enable

WORKDIR /app

COPY --from=workspace package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY package.json apps/frontend/package.json
COPY --from=api_client package.json packages/api-client/package.json
COPY --from=ui package.json packages/ui/package.json

RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter @web-app/frontend...

FROM dependencies AS source

COPY index.html tsconfig.app.json tsconfig.json tsconfig.node.json vite.config.ts apps/frontend/
COPY src apps/frontend/src
COPY --from=api_client src packages/api-client/src
COPY --from=ui src packages/ui/src

FROM source AS development

EXPOSE 5173

FROM source AS builder

RUN pnpm --filter @web-app/frontend build

FROM nginxinc/nginx-unprivileged:1.30.2-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/frontend/dist /usr/share/nginx/html

EXPOSE 8080
