# Dockerfile - Production-ready image
# Stage 1: build & install dependencies
FROM python:3.12-slim AS builder
WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy only the dependency list first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: final minimal runtime image
FROM python:3.12-slim
WORKDIR /app

# Copy installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12

# Copy the rest of the repo
COPY . .

# Expose the Streamlit port
EXPOSE 8501

# Health check against Streamlit's health endpoint
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Run the dashboard
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
