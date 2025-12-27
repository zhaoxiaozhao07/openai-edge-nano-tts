# Stage 1: Build stage
FROM python:3.10-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production stage
FROM python:3.10-slim-bookworm AS production

# Build argument for optional ffmpeg installation
ARG INSTALL_FFMPEG=false

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    if [ "$INSTALL_FFMPEG" = "true" ]; then \
        apt-get install -y --no-install-recommends ffmpeg; \
    fi && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5050

# Expose the port
EXPOSE 5050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5050/')" || exit 1

# Run the application
CMD ["python", "main.py"]
