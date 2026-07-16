FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend folder itself into the container, preserving the directory structure
COPY ./backend /app/backend

# Expose FastAPI's default port
EXPOSE 8000

# Run FastAPI using Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
