set dotenv-load := false
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# Show the available project commands.
default:
    @just --list

# Verify that Docker and the Compose configuration are available.
doctor:
    docker version
    docker compose version
    docker compose config --quiet

# Build and start the complete application, then wait for health checks.
up:
    docker compose config --quiet
    docker compose up --detach --build --wait --remove-orphans
    @echo "FluentStack: http://localhost:5173"
    @echo "API docs:   http://localhost:8001/api/docs"

# Alias for `just up`.
start: up

# Stop and remove project containers without deleting database volumes.
down:
    docker compose down --remove-orphans

# Stop containers but keep them available for a quick start.
stop:
    docker compose stop

# Start existing containers without rebuilding images.
resume:
    docker compose up --detach --no-build --wait --remove-orphans

# Recreate the stack and rebuild changed images.
restart:
    docker compose down --remove-orphans
    docker compose up --detach --build --wait --remove-orphans

# Pull base images and rebuild all application images.
rebuild:
    docker compose pull
    docker compose build --pull
    docker compose up --detach --no-build --wait --remove-orphans

# Show container state and health.
ps:
    docker compose ps

# Follow logs for all services, or pass one service: `just logs backend`.
logs service="":
    docker compose logs --follow --tail 200 {{ service }}

# Run backend tests in the isolated Docker test image.
test:
    docker compose --profile test run --build --rm backend-test

# Compile the production frontend image.
frontend-check:
    docker compose build frontend

# Run backend tests and verify the frontend production build.
check: test frontend-check

# Open a shell inside the running backend container.
shell:
    docker compose exec backend sh

# Print the fully resolved Compose configuration.
config:
    docker compose config
