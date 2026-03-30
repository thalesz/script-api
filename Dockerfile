FROM mcr.microsoft.com/playwright/python:latest

WORKDIR /app

# Copy project
COPY . /app

# Install Python dependencies (project-scoped requirements)
RUN pip install --no-cache-dir -r script/requirements.txt

# Install Playwright browsers (image usually includes browsers, this ensures availability)
RUN python -m playwright install --with-deps

# Copy entrypoint scripts
COPY docker-entrypoint.py /app/docker-entrypoint.py
COPY docker-entrypoint-loader.py /app/docker-entrypoint-loader.py
RUN chmod +x /app/docker-entrypoint.py /app/docker-entrypoint-loader.py

ENV PYTHONUNBUFFERED=1

# Default entrypoint é para scraper (será sobrescrito no loader service)
ENTRYPOINT ["python", "/app/docker-entrypoint.py"]


