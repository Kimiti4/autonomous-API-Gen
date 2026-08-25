# Multi-stage build for the ESAP dashboard.
#
# IMPORTANT: the workflow builds with the REPOSITORY ROOT as context
# (required because the dashboard depends on @esap/observation-client via a
# file: link). All source paths below are therefore relative to the repo root.

# ---- build stage -----------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# 1. Manifests only — maximizes layer-cache hits across source edits.
COPY dashboard/package.json dashboard/package-lock.json ./dashboard/
COPY observation-client/package.json observation-client/package-lock.json ./observation-client/

# 2. Build the observation client first: the dashboard resolves its types and
#    runtime entry points through the file: link, which requires dist/.
RUN cd observation-client \
 && npm ci --no-audit --no-fund \
 && npm run build \
 && rm -rf node_modules

# 3. Install dashboard dependencies (creates the file: symlink).
RUN cd dashboard \
 && npm ci --no-audit --no-fund

# 4. Overlay full sources (client dist already produced above survives the
#    overlay because .dockerignore excludes stale host-side dist output).
COPY observation-client/ ./observation-client/
COPY dashboard/ ./dashboard/

RUN cd dashboard && npm run build

# ---- runtime stage: static assets behind nginx ------------------------------
FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY --from=build /app/dashboard/dist /usr/share/nginx/html
COPY dashboard/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
