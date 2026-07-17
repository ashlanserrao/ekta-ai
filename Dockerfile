FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers embedding model into the image at BUILD time.
# This bakes the RAG model into the container so startup never depends on the network
# (critical for demo venues with flaky/no WiFi).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the backend folder itself into the container, preserving the directory structure
COPY ./backend /app/backend

# Runtime environment:
# - production disables API docs and rejects weak auth secrets
# - offline flags force the RAG model to load from the baked-in cache (no HuggingFace calls)
ENV ENV=production \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# Expose FastAPI's default port
EXPOSE 8000

# Run FastAPI using Uvicorn.
# NOTE: production requires secrets to be supplied at run time, e.g.:
#   docker run --env-file .env -p 8000:8000 <image>
# (at minimum JWT_SECRET and STAFF_PASSCODE; GROQ_API_KEY optional — falls back to mock mode)
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
