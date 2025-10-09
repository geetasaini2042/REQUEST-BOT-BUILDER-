# Base image
FROM python:3.12-slim

# Set workdir
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Expose port (Flask default)
EXPOSE 8000

# Command to run Flask app
CMD ["python", "bot.py"]
