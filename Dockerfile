# Pongogo Knowledge MCP Server Dockerfile
#
# Production deployment for Pongogo MCP server
# Routes to local .pongogo/instructions/ via volume mount

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (git for submodule support if needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy package files for pip install
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY instructions/ ./instructions/
COPY .claude/ ./.claude/

# Install package with dependencies
RUN pip install --no-cache-dir -e .

# Create non-root user for security (MCP best practice)
RUN groupadd -r pongogo && useradd -r -g pongogo pongogo

# Create mount point for project knowledge files
RUN mkdir -p /project/.pongogo/instructions && \
    chown -R pongogo:pongogo /app /project

# Set environment variables
ENV PYTHONUNBUFFERED=1
# Default to project's local instructions (mounted at runtime)
ENV PONGOGO_KNOWLEDGE_PATH=/project/.pongogo/instructions

# Switch to non-root user (security hardening)
USER pongogo

# Run server via entry point
CMD ["pongogo-server"]
