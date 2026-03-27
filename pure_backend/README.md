# Offline Retail Checkout and Entrepreneurship Incubation Middle Platform API (Pure Backend)

## Primary Startup (Required)

```bash
docker compose up
```

For first-time build:
```bash
docker compose up --build
```

No local Python or local PostgreSQL is required.

## Services
- `api`: FastAPI backend
- `db`: PostgreSQL database

## Exposed Ports
- Backend API: `8000:8000`
- PostgreSQL: `5432:5432`

## Addresses
- API root: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`
- Health: `http://localhost:8000/api/v1/health`

## Runtime Behavior
Container startup flow is automatic:
1. wait for PostgreSQL readiness
2. run Alembic migrations
3. run seed bootstrap
4. start FastAPI service

No manual DB import/init step is needed.

## Verification
```bash
curl http://localhost:8000/api/v1/health
docker compose ps
```

## Tests
Inside backend root (`pure_backend/`):

```bash
./run_tests.sh
```

Or specific groups:
```bash
pytest -q unit_tests
pytest -q API_tests
```

## Optional Local Run (Not primary)
A local virtualenv run is possible but not required for acceptance. Docker Compose is the official submission path.

## Notes
- Standard JSON error response format is enforced globally.
- Route-level and object-level authorization checks are active.
- Immutable audit logs and sensitive access logs are implemented.
