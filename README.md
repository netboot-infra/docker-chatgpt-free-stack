# ChatGPT API Project

This project provides two Python scripts for interacting with ChatGPT:
1. `chatgpt.py` - Opens ChatGPT in a browser for interactive use
2. `apigpt.py` - Provides a Flask API for programmatic access to ChatGPT

## Setup

1. Create a virtual environment:
   ```
   python3 -m venv venv
   ```

2. Activate the virtual environment:
   ```
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```
   playwright install chromium
   ```

## Usage

### Interactive Mode
Run the chatgpt.py script to open ChatGPT in a browser:
```
python chatgpt.py
```

To see the browser UI, change `debugBrowser = False` to `debugBrowser = True` in the script.

### API Mode
Run the apigpt.py script to start the Flask API server:
```
python apigpt.py
```

The API will be available at `http://localhost:5001`.

Endpoints:
- POST `/chat` - Send a message to ChatGPT
  Body: `{"message": "Your question here"}`
- GET `/health` - Check if the service is ready

Example API call:
```
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

## Docker

This application can be run as a Docker container.

### Building the Docker Image

```bash
docker build -t chatgpt-api .
```

### Running the Docker Container

```bash
docker run -p 5001:5001 chatgpt-api
```

The API will be available at `http://localhost:5001`.

### Using Docker Hub

To pull and run the pre-built image from Docker Hub:

```bash
docker pull your-dockerhub-username/chatgpt-api
docker run -p 5001:5001 your-dockerhub-username/chatgpt-api
```

Replace `your-dockerhub-username` with your actual Docker Hub username.
