# Convergence demo — one-command run.
#   docker build -t convergence .
#   docker run --rm -p 8765:8765 convergence      # open http://127.0.0.1:8765/
#
# The engine core is stdlib-only, so the image installs no runtime deps. The
# optional chat backends are not installed here; pass keys + `pip install
# .[llm]` in a derived image if you want live narration.
FROM python:3.12-slim

WORKDIR /app

# Install first against just the metadata so the layer caches across code edits.
COPY pyproject.toml README.md ./
COPY convergence ./convergence
COPY web ./web
COPY data ./data
COPY demo.py ./
# Editable install: the app resolves its corpora via the package location
# (web/../data), so the source tree must stay in place at runtime.
RUN pip install --no-cache-dir -e .

# Containers must bind 0.0.0.0 to be reachable; the app still defaults to
# localhost everywhere else. /api/chat proxies to paid LLM backends, so
# CONVERGENCE_API_KEY is required for any exposed deployment — set it via
# `-e CONVERGENCE_API_KEY=<key>` on `docker run` (see README and SECURITY.md).
ENV CONVERGENCE_HOST=0.0.0.0
EXPOSE 8765

CMD ["convergence-web"]
