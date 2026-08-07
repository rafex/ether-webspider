# Justfile — Task runner for ether-webspider
#
# Usage:
#   just          — list available tasks
#   just up       — start ether-websearch REST + MCP
#   just down     — stop services
#   just test     — run tests with coverage
#   just lint     — ruff check + format check
#   just typecheck — mypy

default:
    @just --list

# ── Development ────────────────────────────────────────────────────────────────

# Install dependencies in venv
install:
    uv venv --python 3.11 || true
    uv pip install -e ".[dev]"

# Run lint (ruff check + format check)
lint:
    ruff check webspider/ tests/
    ruff format --check webspider/ tests/

# Fix lint issues automatically
lint-fix:
    ruff check --fix webspider/ tests/
    ruff format webspider/ tests/

# Run mypy type checker
typecheck:
    mypy webspider/

# Run tests with coverage
test:
    pytest tests/ -v --cov=webspider --cov-report=term-missing

# Run a specific test file
test-file file:
    pytest {{file}} -v

# ── Services (ether-websearch) ──────────────────────────────────────────────────

# Start ether-websearch REST + MCP services
up websearch_repo="../ether-websearch":
    @echo "Starting ether-websearch REST API on port 8766..."
    cd {{websearch_repo}} && \
    MCP_REST_BASE_URL="http://127.0.0.1:8766" \
    {{websearch_repo}}/.venv/bin/uvicorn websearch.src.api.server:app \
        --host 127.0.0.1 --port 8766 &

# Stop services
down:
    @echo "Stopping services..."
    pkill -f "uvicorn websearch.src.api.server" 2>/dev/null || true
    pkill -f "websearch.src.mcp.mcp_server" 2>/dev/null || true
    echo "Done."

# ── Execution ──────────────────────────────────────────────────────────────────

# Run a demo mission against a test site
demo:
    python -m webspider.cli run \
        --goal "Find all book category pages" \
        --start https://books.toscrape.com \
        --max-steps 15

# ── Maintenance ─────────────────────────────────────────────────────────────────

# Remove checkpoints older than 7 days
clean-checkpoints:
    find checkpoints -type d -mindepth 1 -mtime +7 -exec rm -rf {} + 2>/dev/null || true

# Clean all artifacts
clean: clean-checkpoints
    rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
