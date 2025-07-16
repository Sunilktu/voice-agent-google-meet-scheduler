FROM python:3.10-slim

# Set working directory
WORKDIR /app


# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential curl git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install --no-cache-dir uv



# Copy dependency definition files first for caching
COPY pyproject.toml /app/

# Install dependencies globally (no venv)
RUN uv sync

# Now copy the rest of the code
COPY . /app/

# Expose application port (example: Streamlit)
EXPOSE 8501

# Default command (update if needed)
CMD ["uv", "run", "Streamlit","run", "main.py"]
