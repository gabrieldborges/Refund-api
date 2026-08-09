# Packages the API so it runs the same way everywhere, instead of depending on
# somebody rebuilding the environment by hand. The README's seven local steps
# are one `docker run` here — and the class of failure that produced them is
# recorded in this project: a venv that was not activated, a venv with stale
# shebangs, and a CI that has to pin python-version because the local
# interpreter is older than the runner's default.

# ---------------------------------------------------------------- build stage
# Two stages so the compilers and pip's caches stay OUT of what ships. The
# final image copies the finished virtualenv and nothing else from here.
FROM python:3.9-slim AS builder

# gcc is needed to build the wheels that have no prebuilt one for slim, and
# this is exactly the kind of thing that must not travel to the runtime image.
RUN apt-get update \
    && apt-get install --no-install-recommends -y gcc \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copied alone, before the source, so an unchanged requirements.txt reuses the
# cached install layer — editing a controller does not reinstall SQLAlchemy.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------------------------------------- runtime stage
FROM python:3.9-slim

# NOT root. A process that gets compromised is then confined to what this user
# can touch, rather than owning the container. --system because nobody logs in
# as this account.
RUN useradd --system --create-home --uid 1001 refund

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY --chown=refund:refund alembic.ini ./
COPY --chown=refund:refund alembic ./alembic
COPY --chown=refund:refund init ./init
COPY --chown=refund:refund src ./src

USER refund

EXPOSE 3333

# LIVENESS only. /ready is the database check, and it is deliberately NOT used
# here: Docker restarts a container whose healthcheck fails, so pointing this
# at /ready would make a database outage restart every instance in a loop —
# turning something recoverable into an outage. An orchestrator asks /ready
# separately, to decide about traffic rather than about restarting.
#
# Written in Python because the slim image has no curl, and adding one for a
# healthcheck would put a network tool in the runtime image for no other
# reason.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:3333/health', timeout=2).status == 200 else 1)"

# NO SECRETS HERE, and none anywhere above. Every value the app needs arrives
# as an environment variable at run time and is validated at startup by
# Settings (Item 17) — a missing one stops the process with a message naming
# it, rather than failing later. The .env is excluded by .dockerignore.
#
# NOTE ON STORAGE: with STORAGE_BACKEND=local this container writes uploads to
# its own filesystem, which disappears on every restart — silently, since the
# database row survives. Deploy it with STORAGE_BACKEND=s3. That is the whole
# point of Item 22, and a container is where the ephemeral disk stops being
# theoretical.
CMD ["uvicorn", "src.main.server.server:app", "--host", "0.0.0.0", "--port", "3333"]
