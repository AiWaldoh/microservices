# Web Article Summarizer

This project is a web article summarizer that uses Scrapy for web scraping, `newspaper3k` for article text extraction, and Gensim or spaCy for summarization. It's designed to handle dynamically loaded content and provides an API endpoint for easy integration. The project is managed with Poetry for dependency management and packaged with Docker for easy deployment as part of a multi-service architecture.

## Features

- Web scraping with Scrapy and Playwright for JavaScript-rendered pages.
- Article text extraction using `newspaper3k`.
- Text summarization using summa.
- FastAPI for creating an API endpoint.
- Managed with Poetry for streamlined dependency management.
- Dockerized application for easy deployment and scalability.
- Integration with Docker Compose for multi-service orchestration.

## Installation

### Using Poetry

Ensure you have Poetry installed. Then, clone the repository and install the dependencies:

    poetry install

### Using Docker

Build the Docker image:

    docker build -t article-summarizer .

### Using Docker Compose

If you're running this service as part of a multi-service architecture with Docker Compose, include it in your `docker-compose.yml` file:

    version: '3.8'

    services:
      webpage_summarizer_service:
        build: ./top_secret/services/webpage_summarizer_service
        network_mode: host
        # Other services and configurations...

## Usage

### Running the Server

To start the FastAPI server with Poetry:

    poetry run uvicorn main:app --reload

Replace `main` with the name of your Python script.

### Running with Docker

To run the Docker container:

    docker run -p 8000:8000 article-summarizer

### Running with Docker Compose

To start all services defined in your `docker-compose.yml`:

    docker-compose up

## API Endpoint

The `/scrape-url` endpoint accepts POST requests with the following JSON structure:

    {
        "url": "http://example.com",
        "parse_method": "css",
        "parse_expression": "body"
    }

It returns the scraped article's text and a summary.

## Example

To scrape an article, send a POST request to `/scrape-url` with the target URL and parsing details. The response will include the extracted text and its summary.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
