# Refund API

Backend of the refund-request system, organized with Clean Architecture. The
sibling frontend lives in [`Refund`](https://github.com/gabrieldborges/Refund).

The product requirements and shared decisions live in the
[canonical documentation](docs/index.md). Architecture decisions are recorded
as ADRs in [`docs/decisions/`](docs/decisions/).

**Live API:** https://refund-api-production-5a7c.up.railway.app/health
**Live app:** https://independent-fascination-production-feea.up.railway.app/

## Environment setup

Copy [`.env.example`](.env.example) to `.env` and fill it in:

```bash
cp .env.example .env
```

`usuario`, `senha` and `host` are example values: replace them with your
environment's credentials. Never commit `.env` (it is already in `.gitignore`)
and never expose real credentials in the documentation.

Only two variables are **required**: `DATABASE_URL` and `JWT_SECRET`. The
others have defaults. The full list, with defaults, is in `.env.example`.

Configuration is validated at startup by `src/configs/settings.py`
([ADR-004](docs/decisions/ADR-004-typed-settings.md)): if a required variable
is missing or has an invalid type, the application **does not start** and the
error names the field. Before this, a missing `JWT_SECRET` let the application
start normally and fail only at a user's first login.

The test suite does **not** use your `.env`: the root `conftest.py` pins fake
values, so `pytest` works even without `.env` and never reaches the real
database.

## Running locally

**Requires Python 3.13**, the same version as CI and the image
(`python:3.13-slim`). The floor is `>= 3.10`, and it comes from nine pinned
packages that declare `Requires-Python: >=3.10` (among them `fastapi`,
`starlette`, `urllib3` and `pytest`); below that, `pip` refuses the set. Worth
checking before creating the venv, since on many systems the `python3` on PATH
is still an old version:

```bash
python3 --version   # must be 3.10+; the project uses 3.13
```

1. Create and activate the virtual environment, and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt   # runtime + test and lint
   ```

2. Apply the migrations (required before starting the server for the first
   time; without it the first request fails with `UndefinedTable`):

   ```bash
   alembic upgrade head
   ```

   The database schema is governed by Alembic (`alembic/versions/`). Running
   `alembic upgrade head` is safe at any time: it applies only the migrations
   that are missing. `init/schema.sql` still exists only as historical
   reference.

3. Start the server:

   ```bash
   python run.py
   ```

The API starts at `http://localhost:3333`.
Automatic documentation (Swagger) at `http://localhost:3333/docs`.

## Health endpoints

They are **two different questions**, and confusing them has a practical
consequence:

| Endpoint | Question | If it fails, the orchestrator should |
|---|---|---|
| `GET /health` | is the process alive? | **restart** |
| `GET /ready` | can it serve? | **stop sending traffic** |

`/health` queries nothing, on purpose: if it failed during a database outage,
every instance would be restarted in a loop, and a recoverable outage would
become a blackout. `/ready` queries the database and answers `503` while it is
unreachable, returning to `200` on its own when it comes back.

For the same reason, the `HEALTHCHECK` in the `Dockerfile` points to `/health`,
never to `/ready`.

## Production

The project has been deployed since 2026-08-10. The API runs on **Railway**, in
a container built from this repository's `Dockerfile`; the database is
**Railway's PostgreSQL**; files live in an **AWS S3 bucket**; and the frontend is
served as static files by another Railway service (see the `README.md` of
[`Refund`](https://github.com/gabrieldborges/Refund)).

To know whether it is up right now, rather than trusting this section:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://refund-api-production-5a7c.up.railway.app/health
curl -s -o /dev/null -w '%{http_code}\n' https://refund-api-production-5a7c.up.railway.app/ready
```

`/health` is liveness and `/ready` queries the database; both at 200 mean the
process is alive **and** the database is reachable.

### Production variables — NAMES, never values

No production value lives in this repository. The list below is what must exist
in the provider's environment; the defaults and format of each are in
[`.env.example`](.env.example).

| Variable | Why it matters in production |
|---|---|
| `DATABASE_URL` | **needs the `postgresql+asyncpg` dialect**, see the warning below |
| `JWT_SECRET` | required; signs login **and** the file URLs of the `local` backend |
| `ENVIRONMENT` | with `production`, startup refuses `CORS_ORIGINS` containing `*`, `localhost` or `127.0.0.1` |
| `CORS_ORIGINS` | must contain the deployed frontend's domain |
| `PUBLIC_BASE_URL` | the API's own public domain |
| `STORAGE_BACKEND` | **`s3` in production**; with `local`, every file evaporates on redeploy |
| `S3_BUCKET`, `S3_REGION` | the bucket and its region |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | credentials of the IAM user restricted to the bucket |
| `S3_ENDPOINT_URL` | **leave EMPTY on real AWS**; only set for MinIO or another compatible provider |
| `LOG_LEVEL`, `JWT_ALGORITHM`, `JWT_EXPIRATION_HOURS`, `FILE_URL_TTL_SECONDS` | have defaults; only set to change the default |

`PORT` is **not** configured by you: the platform injects it, and the container
listens on it. Without `PORT`, the default of 3333 still applies, so a local
`docker run` works the same way.

**The `DATABASE_URL` the provider injects is wrong for this project.** It
arrives in libpq form (`postgresql://...`), which SQLAlchemy resolves to a
**synchronous** driver that is not installed here. Since the URL parses without
complaint and the engine is lazy, the application **started healthy and died on
the first query**. Since 2026-08-10 `Settings` refuses to start in that case,
and the error says what to write: `postgresql+asyncpg://...`.

**Before the first access, apply the migrations** (`alembic upgrade head`) and
promote the first admin (`python -m init.promote_admin <email>`, on an account
already registered). Public sign-up always creates `standard` (BR-003).

## Orphan file sweep

An orphan file is a file on disk (or in the bucket) that **no database row
references**. They appear through two paths that no in-process compensation
reaches: a `SIGKILL` between writing the file and committing the row, and a file
deletion that fails **after** the commit. In that case the response is a
success, correctly, and the file stays.

```bash
python -m init.sweep_orphans            # reports, removes nothing
python -m init.sweep_orphans --apply    # removes what it reported
```

**Reports by default, on purpose.** This deletes user files; a command that
removes on the first run, when someone runs it to see what it does, ends up
removing something it should not.

**Only files older than one hour count as orphans.** A file written two seconds
ago, whose transaction has not committed yet, is indistinguishable from an
orphan, and deleting it would destroy a receipt in flight. One hour is far more
than any request here takes.

Running it twice is safe: the second run finds nothing, because the first
already removed it.

## Secret rotation

There is no automation for this. It is a procedure, and it is written down
because a secret nobody knows how to rotate does not get rotated.

**`JWT_SECRET`.** Rotating it **invalidates every active session**: tokens in
circulation were signed with the old key and start failing verification, so
every user is logged out. There is no zero-downtime rotation today. Supporting
two keys at once (verify with old and new, sign only with new) is what would
allow it, and it does not exist. **Since 2026-08-10 this stopped being
hypothetical:** there is production, so there are real sessions to drop.

Rotating also **invalidates signed file URLs in flight** (Item 22), which are
signed with the same key. Since they expire in 5 minutes, the practical effect
is a broken image for a few minutes, not data loss.

**`S3_SECRET_ACCESS_KEY`.** Generate the new key at the provider, update the
variable, and only then revoke the old one, in that order, or there is a window
in which no upload works.

**`DATABASE_URL`.** Rotating the database password drops the pool's
connections. With one instance, restarting the process after the change is
enough. Note that the rotated value must keep the `postgresql+asyncpg` dialect:
the provider returns the libpq form, and startup refuses the synchronous form.

**When to rotate:** on suspected exposure, when revoking access from someone who
had the values, and **whenever a development value was promoted to
production**. This section used to list a third trigger, "before the first real
deploy, because the current values were born in development and have circulated
in terminals", which the 2026-08-10 deploy passed. **Which production value is
new and which was reused from development is not recorded here, and cannot be
deduced**: only whoever configured the dashboard knows. Anyone who wants the
guarantee should rotate, not check. The cost of rotating unnecessarily is one
dropped session; the cost of not rotating a reused value is a production secret
that already circulated in a terminal.

## Tests

There are two suites, separated by pytest marker.

```bash
pytest                  # the mocked suite: fast, no database, no Docker
pytest -m integration   # against a real PostgreSQL (needs the container)
```

The first runs all the time and **requires nothing beyond the dependencies**.
The second needs the disposable database:

```bash
docker compose up -d    # PostgreSQL 18 (port 5433) + MinIO (port 9100)
pytest -m integration
docker compose down     # throw it away
```

The container is pinned to the **same major version as production** (Neon
reports 18.4). Testing against another major would hide exactly the differences
the integration tests exist to expose, which is why SQLite is not an option
here, not even as a local shortcut.

What each suite reaches: the mocked one proves the repositories **build** the
right SQL; the integration one proves PostgreSQL **accepts** that SQL and
behaves as we assume: constraints, schema defaults, foreign keys, real
aggregates, and `lock_timeout` under row contention. MinIO plays the same role
for object storage: the `S3FileStorage` tests write to a real bucket and
download through a real presigned URL.

## File storage

Two implementations of the same interface, chosen by `STORAGE_BACKEND`:

| | `local` (default) | `s3` |
|---|---|---|
| Where the file lives | instance disk | S3-compatible bucket |
| Survives a redeploy | **no** | yes |
| How the URL is signed | short-lived JWT from this API | provider presigned URL |

The file routes (`/refunds/{id}/receipt`, `/refunds/{id}/payment-receipt`,
`/users/{id}/avatar`) return **a URL**, not the bytes. That is what lets an
`<img src>` work, since an `<img>` tag cannot send `Authorization: Bearer`.

Authorization is still checked before the URL is generated; what changes is
that it stays valid for `FILE_URL_TTL_SECONDS` (default 300s) instead of being
re-checked on every request. See
[ADR-003](docs/decisions/ADR-003-local-receipt-storage.md).

## Structure

Follows the same layered pattern as the other Python projects:

```
src/
├── models/{entities,repositories,settings}   # entities, data access, connection
├── controllers/                              # business rules
├── views/                                    # HTTP adapter
├── validators/                               # input validation (Pydantic)
├── errors/                                   # custom errors + central handler
└── main/{composer,routes,server}             # dependency injection and bootstrap
```

Uploaded receipt files live in `uploads/receipts/`; profile photos in
`uploads/avatars/`; payment receipts in `uploads/payment_receipts/`. None of the
three directories is served statically. All require a valid JWT and are
obtained, respectively, through `GET /refunds/{refund_id}/receipt`,
`GET /users/{user_id}/avatar` and `GET /refunds/{refund_id}/payment-receipt`.

## Authentication

- `POST /auth/register` — `{name, email, password}`. Always creates a user with
  role `standard` (role is not accepted from the client).
- `POST /auth/login` — `{email, password}`. Returns a JWT (`token`) carrying
  `user_id` and `role`, expiring in `JWT_EXPIRATION_HOURS`.
- Protected routes must use `Depends(get_current_user)`
  (`src/main/middlewares/auth_jwt.py`), passing the token in the
  `Authorization: Bearer <token>` header.

## Testing with Postman

Import [`Refund-api.postman_collection.json`](Refund-api.postman_collection.json)
(File > Import). The collection ships with:
- A `host` variable (`http://localhost:3333`).
- **Auth - Login** saves the token automatically into the `{{token}}` variable
  (script in the Tests tab); the other requests already use
  `Authorization: Bearer {{token}}`.
- **Refunds - Create** saves the created `id` in `{{refund_id}}`, used by
  **Get by ID**, **Review Status** and **Delete**.
- Run in order: Register → Login → Create → List → Get by ID → Review Status
  → Delete.
- **Review Status** only works logged in as `admin` (promote a user directly in
  the database, since public sign-up always creates `standard`, BR-003) and
  different from the request's owner (BR-016); with a `standard` user, or
  reviewing your own request, the API answers `403`.
- Note that **Review Status** decides the request (`approved` or `rejected`),
  and a decided request can no longer be deleted (BR-015): running **Delete**
  after **Review Status** on the same `refund_id` answers `422`. To test the
  full deletion flow, create a second request and skip **Review Status** for it.
