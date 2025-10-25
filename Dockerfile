# Use a small Python base image
FROM python:3.10-slim

# Make a directory for your app's files
WORKDIR /app

# Copy and install dependencies
# (include "gunicorn" in requirements or install it separately)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all remaining files
COPY . .

# Expose the default Spaces port
ENV PORT 7860

# Use Gunicorn to run the Dash app with 1 worker, 4 threads on HF toaster
CMD gunicorn app:server --workers 1 --threads 4 -b 0.0.0.0:$PORT
