# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Default command (overridden by docker-compose)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
