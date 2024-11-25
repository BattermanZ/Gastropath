# Use the Python slim image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system-level dependencies that are often required
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt requirements.txt

# Install the required Python packages using requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Set environment variables
ENV FLASK_APP=gastropath_server.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=3754

# Expose port 3754 for Flask server
EXPOSE 3754

# Run the Flask server when the container starts
CMD ["flask", "run"]