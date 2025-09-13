# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files to the container
COPY pyproject.toml poetry.lock /app/

# Install Poetry
RUN pip install poetry

# Install dependencies
RUN poetry install --no-root

# Copy the rest of the application code to the container
COPY . /app

# Expose port 8000
EXPOSE 8000

# Command to run the FastAPI server
CMD ["poetry", "run", "fastapi", "run", "app/main.py", "--port", "8000"]
