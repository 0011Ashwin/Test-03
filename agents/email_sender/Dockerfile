FROM python:3.12-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory and copy source
WORKDIR /app
COPY . /app

# Optimize Python logs
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install absolute dependencies using uv
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv sync --active

# Expose the standard Cloud Run port
EXPOSE 8080

# Start the ADK agent engine
CMD python3 adk_app.py --host 0.0.0.0 --port ${PORT:-8080} --trace_to_cloud --a2a
