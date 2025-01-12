# Use a small Python base image
FROM python:3.10-slim

# Make a directory for your app's files
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all remaining files
COPY . .

# Expose the default Spaces port
ENV PORT 7860

# Run your app
CMD ["python", "app.py"]
