# VibeGrade Backend Dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for ESLint/TypeScript
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install static analysis tools globally
RUN npm install -g eslint typescript && \
    pip install --no-cache-dir semgrep trivy detect-secrets

# Create non-root user for sandbox
RUN useradd -u 10001 -r -g nogroup -m -d /home/scanner -s /bin/bash scanner

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY alembic ./alembic
COPY app ./app

# Create directory for rubric
RUN mkdir -p /app/rubric

# Expose port
EXPOSE 8000

# Run as non-root user
USER scanner

# Default command
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]