# Use a slim version of the official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy only the requirements.txt file to leverage Docker cache
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code
COPY . .

# Set environment variables
ENV PORT=8009 \
    MODEL_PATH=/app/models/TheBloke_gorilla-openfunctions-v1-GPTQ

# Make port 8008 available to the world outside this container
EXPOSE 8009

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8009"]
