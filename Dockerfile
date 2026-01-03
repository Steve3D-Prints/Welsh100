FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app and data
COPY welsh100.py .
COPY welsh_100.csv .

# Create directory for persistent photos
RUN mkdir -p /data/photos

# Healthcheck to keep it running smoothly
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "welsh100.py", "--server.port=8501", "--server.address=0.0.0.0"]