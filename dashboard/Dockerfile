# Multi-stage build for the ESAP dashboard.
#
# IMPORTANT: the workflow builds with the REPOSITORY ROOT as context
# (required because the dashboard depends on @esap/observation-client via a
# file: link). All source paths below are therefore relative to the repo root.
# Layer order: manifests+configs -> installs -> full sources -> builds.

# ---- build stage -----------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# 1. Client manifests + compiler configs; install its dependencies.
COPY observation-client/package.json observation-client/package-lock.json \
     observation-client/tsconfig.json observation-client/tsconfig.build.json \
     ./observation-client/
RUN cd observation-client && npm ci --no-audit --no-fund

# 2. Dashboard manifests; install (file: link target already exists above).
COPY dashboard/package.json dashboard/package-lock.json ./dashboard/
RUN cd dashboard && npm ci --no-audit --no-fund

# 3. Overlay full sources (root .dockerignore excludes node_modules/dist so
#    image-side state from steps 1-2 is preserved, not clobbered).
COPY observation-client/ ./observation-client/
COPY dashboard/ ./dashboard/

# 4. Build client (produces dist/ consumed through the file: link), then app.
RUN cd observation-client && npm run build \
 && cd ../dashboard && npm run build

# ---- runtime stage: static assets behind nginx ------------------------------
FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY --from=build /app/dashboard/dist /usr/share/nginx/html
COPY dashboard/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
