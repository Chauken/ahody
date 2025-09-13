# articler
Article + Scraper = Articler

A simple app that scrapes the contents of an article for a given URL. This project is built using Python and leverages FastAPI for the backend. It is containerized using Docker for easy deployment and development.


Project structure heavily inspired by the backend part of [FastAPI Fullstack Template](https://github.com/fastapi/full-stack-fastapi-template/tree/master/backend).

## How to Run Articler for Production

### Using Docker Compose
1. Ensure you have Docker installed on your system.
2. Build and start the Docker compose container
    ```bash
    docker compose up
    ```

### Using Standalone Docker
1. Ensure you have Docker installed on your system.
2. Build the Docker image:
   ```bash
   docker build -t articler .
   ```
3. Run the Docker image:
    ```bash
    docker run --name -p 8000:8000 articler
    ```

## Continue Development

1. Prerequisites
   - Python 3.12+
   - Poetry (for dependency management)
   - Docker (optional, for containerization)

2. Install dependencies
    ```bash
    poetry install --no-root
    ```

3. Start Python environment
    ```bash
    poetry shell
    # or
    poetry env activate
    ```

4. Run the application
    ```bash
    fastapi dev main/app.py --reload
    ```
