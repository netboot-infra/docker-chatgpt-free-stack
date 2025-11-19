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