# VibeGrade Sandbox Dockerfile
# Used for secure runtime verification of untrusted code

FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for JS/TS projects
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Rust
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Install Go
ENV GOPATH=/go \
    PATH=/go/bin:$PATH
RUN curl -fsSL https://go.dev/dl/go1.21.5.linux-amd64.tar.gz | tar -C /usr/local -xz

# Create non-root user for sandbox
RUN useradd -u 10001 -r -g nogroup -m -d /home/scanner -s /bin/bash scanner

# Set working directory
WORKDIR /workspace

# Copy sandbox runner script
COPY sandbox_runner.py /usr/local/bin/sandbox_runner.py
RUN chmod +x /usr/local/bin/sandbox_runner.py

# Switch to non-root user
USER scanner

# Default command
CMD ["python", "/usr/local/bin/sandbox_runner.py"]