# File: apigpt.py
# Run with: python apigpt.py

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import random
import signal
import threading
import queue
import uuid
import os  # Bổ sung
from functools import wraps  # Bổ sung
from flask import Flask, request, jsonify, Response
import json
from flask_cors import CORS
# ----------------------------------------------------------------------
#                          CONFIGURATION
# ----------------------------------------------------------------------
SESSION_TIMEOUT_MINUTES = 12  # Increased to 12 minutes to reduce login frequency
SHUTDOWN_TIMEOUT = SESSION_TIMEOUT_MINUTES * 60
HEADLESS_MODE = True

# --- AUTHENTICATION CONFIG ---
# Lấy key từ biến môi trường hoặc dùng key mặc định
API_TOKEN = os.environ.get(
    "CHATGPT_API_KEY", "dung1234aA@$")

# ----------------------------------------------------------------------
#                  HÀM MÔ PHỎNG HÀNH VI (GIỮ NGUYÊN)
# ----------------------------------------------------------------------


def simulate_human_mouse_movement(page, start_x, start_y, end_x, end_y, duration=1.0):
    """Simulate human-like mouse movement"""
    num_points = random.randint(10, 20)
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        x = start_x + (end_x - start_x) * t + random.randint(-20, 20)
        y = start_y + (end_y - start_y) * t + random.randint(-20, 20)
        points.append((x, y))

    for i, (x, y) in enumerate(points):
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.01, duration/len(points)))


def simulate_human_click(page, x, y):
    """Simulate human-like clicking"""
    current_pos = (random.randint(0, 1920), random.randint(0, 1080))
    simulate_human_mouse_movement(
        page, current_pos[0], current_pos[1], x, y, random.uniform(0.5, 1.5))
    time.sleep(random.uniform(0.1, 0.3))
    click_x = x + random.randint(-2, 2)
    click_y = y + random.randint(-2, 2)
    page.mouse.click(click_x, click_y)
    time.sleep(random.uniform(0.1, 0.2))


def simulate_human_typing(page, selector, text):
    """Simulate human-like typing"""
    page.click(selector)
    time.sleep(random.uniform(0.1, 0.3))
    typed_text = ""
    for char in text:
        if random.random() < 0.02:  # 2% chance of typo
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            page.type(selector, wrong_char)
            typed_text += wrong_char
            time.sleep(random.uniform(0.05, 0.15))
            page.press(selector, "Backspace")
            typed_text = typed_text[:-1]
            time.sleep(random.uniform(0.05, 0.1))

        page.type(selector, char)
        typed_text += char
        if char == " ":
            time.sleep(random.uniform(0.05, 0.15))
        elif char in ",.!?:;":
            time.sleep(random.uniform(0.1, 0.2))
        else:
            time.sleep(random.uniform(0.02, 0.1))
    return typed_text

# ----------------------------------------------------------------------
#                     BROWSER WORKER (THE CORE FIX)
# ----------------------------------------------------------------------
# This class runs on a separate thread. Flask only sends tasks here.


class BrowserWorker(threading.Thread):
    def __init__(self):
        super().__init__()
        self.task_queue = queue.Queue()
        self.daemon = True
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.ready = False
        self.last_activity = time.time()
        self.is_running = True
        self.sysprompt_sent = False  # Track if sysprompt has been sent

    def run(self):
        print("--- Browser Worker Thread Started ---")
        while self.is_running:
            try:
                # Wait for task up to 1 second, then check timeout
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    self._check_idle_timeout()
                    continue

                task_type = task.get('type')

                if task_type == 'shutdown_app':
                    self._shutdown_browser()
                    self.is_running = False
                    break

                elif task_type == 'chat':
                    result_queue = task.get('result_queue')
                    message = task.get('message')
                    response = self._process_chat(message)
                    result_queue.put(response)

                self.task_queue.task_done()

            except Exception as e:
                print(f"Fatal error in Worker Loop: {e}")

    def _check_idle_timeout(self):
        """Check if inactive for too long then close browser"""
        if self.ready and (time.time() - self.last_activity > SHUTDOWN_TIMEOUT):
            print(
                f"--- Timeout {SESSION_TIMEOUT_MINUTES}m. Closing browser to free up RAM. ---")
            self._shutdown_browser()

    def _init_browser(self):
        """Initialize Playwright (Only runs in Worker Thread)"""
        if self.ready:
            return True

        print("--- Initializing ChatGPT Browser... ---")
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=HEADLESS_MODE,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                    "--disable-infobars",
                    "--disable-extensions",
                ]
            )

            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                java_script_enabled=True,
                bypass_csp=True,
                extra_http_headers={
                    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not=A?Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"macOS"',
                    "accept-language": "en-US,en;q=0.9",
                }
            )

            self.page = self.context.new_page()
            stealth = Stealth()
            stealth.apply_stealth_sync(self.page)

            print("Accessing https://chatgpt.com ...")
            self.page.goto("https://chatgpt.com", timeout=60000)

            # Wait for page to fully load
            self.page.wait_for_load_state("domcontentloaded")
            # Additional wait (OpenAI sometimes loads slowly)
            time.sleep(5)

            # Handle Guest login if present
            try:
                login_prompt = self.page.query_selector(
                    'div.flex.flex-col.items-center.justify-center.px-6.py-8')
                if login_prompt:
                    # Look for the "Continue as guest" link
                    continue_as_guest = login_prompt.query_selector(
                        'a.cursor-pointer')
                    if continue_as_guest:
                        # Get the bounding box for human-like clicking
                        bbox = continue_as_guest.bounding_box()
                        if bbox:
                            center_x = bbox['x'] + bbox['width'] / 2
                            center_y = bbox['y'] + bbox['height'] / 2
                            simulate_human_click(self.page, center_x, center_y)
                        else:
                            # Fallback if we can't get bounding box
                            continue_as_guest.click()
                        # Wait a bit for the prompt to disappear
                        time.sleep(2)
            except:
                pass  # If we can't handle the login prompt, continue anyway

            self.ready = True
            self.last_activity = time.time()
            self.sysprompt_sent = False  # Reset sysprompt sent flag on new browser session
            print("--- Initialization successful ---")
            return True
        except Exception as e:
            print(f"Initialization error: {e}")
            self._shutdown_browser()
            return False

    def _shutdown_browser(self):
        """Close browser safely"""
        print("--- Closing browser... ---")
        if self.context:
            try:
                self.context.close()
            except:
                pass
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.ready = False

    def _send_message(self, message, human_typing=True):
        """Send a message to ChatGPT"""
        page = self.page

        # --- PROCESS TEXTAREA ---
        # Increase timeout to 10s
        try:
            textarea = page.wait_for_selector(
                'div.ProseMirror#prompt-textarea', state='visible', timeout=10000)
            if not textarea:
                raise Exception("Could not find input field")
        except:
            # Fallback: Sometimes class changes, try clicking on body then search again
            page.mouse.click(500, 500)
            textarea = page.wait_for_selector(
                '#prompt-textarea', state='visible', timeout=5000)

        # Fill textarea directly or simulate human typing based on flag
        if human_typing:
            simulate_human_typing(
                page, 'div.ProseMirror#prompt-textarea', message)
        else:
            # Fill directly without human simulation
            textarea.fill(message)

        # Click send
        send_btn = page.query_selector('button[data-testid="send-button"]')
        if send_btn:
            send_btn.click()
        else:
            page.keyboard.press("Enter")

    def _wait_for_response(self):
        """Wait for ChatGPT response to complete"""
        page = self.page

        # Show loading indicator with animation
        loading_chars = ["⠋", "⠙", "⠹", "⠸",
                         "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        loading_index = 0

        # Wait for the response to complete with visual feedback
        response_started = False
        start_time = time.time()
        timeout = 30  # seconds

        try:
            # Wait for the stop button to appear (response started)
            page.wait_for_selector(
                'button[data-testid="stop-button"]', timeout=5000)
            response_started = True

            # Show loading animation while waiting for response to complete
            while response_started and (time.time() - start_time) < timeout:
                try:
                    # Check if stop button still exists
                    stop_button = page.query_selector(
                        'button[data-testid="stop-button"]')

                    # If stop button is gone, response is complete
                    if stop_button is None:
                        response_started = False
                        break

                    # Update loading animation
                    loading_index += 1
                    time.sleep(0.1)
                except:
                    response_started = False
                    break
        except:
            # If we can't detect the stop button, show simple loading
            time.sleep(2)  # Reduced from 3 to 2 seconds

    def _process_chat(self, message):
        """Process chat logic"""
        self.last_activity = time.time()

        # 1. Ensure browser is open
        if not self._init_browser():
            return {"error": "Could not initialize browser"}

        try:
            page = self.page

            # Send sysprompt as the first message if not already sent
            if not self.sysprompt_sent:
                try:
                    # Read entire sysprompt file once and send it
                    try:
                        with open('sysprompt.txt', 'r', encoding='utf-8') as f:
                            sysprompt_content = f.read()
                        if sysprompt_content.strip():
                            print("Sending system prompt as first message...")
                            self._send_message(
                                sysprompt_content, human_typing=False)
                            # Wait for response to complete
                            self._wait_for_response()
                    except FileNotFoundError:
                        print(
                            "sysprompt.txt not found, continuing without system prompt...")
                except Exception as e:
                    print(f"Error sending system prompt: {e}")
                finally:
                    self.sysprompt_sent = True

            # Check for rate limit modal and handle it
            try:
                rate_limit_modal = page.query_selector(
                    'div[data-testid="modal-no-auth-rate-limit"]')
                if rate_limit_modal:
                    # Look for the "Stay logged out" link
                    stay_logged_out = rate_limit_modal.query_selector(
                        'a.cursor-pointer')
                    if stay_logged_out:
                        print(
                            "Clicking 'Stay logged out' to dismiss rate limit modal...")
                        stay_logged_out.click()
                        # Wait a bit for the modal to disappear
                        time.sleep(2)
            except Exception as modal_error:
                print(f"Error handling rate limit modal: {modal_error}")
                pass  # Continue anyway if we can't handle the modal

            # Send user message and wait for response
            self._send_message(message)
            self._wait_for_response()

            # Try to extract the latest response
            try:
                # Wait for response elements to appear
                page.wait_for_selector(
                    'div.markdown.prose', timeout=10000)

                # Reduce the wait time for the text to fully render
                time.sleep(0.5)

                # Get all response elements
                response_elements = page.query_selector_all(
                    'div.markdown.prose')

                if response_elements:
                    # Get the last response (most recent one)
                    latest_response = response_elements[-1]
                    response_text = latest_response.inner_text()

                    # Standardize the response text by removing newlines and extra whitespace
                    standardized_response = ' '.join(response_text.split())

                    return {"response": standardized_response}
                else:
                    return {"error": "Could not find response from ChatGPT."}

            except Exception as response_error:
                return {"error": f"Could not extract response: {response_error}"}

        except Exception as e:
            print(f"Error during chat process: {e}")
            self._shutdown_browser()  # Reset nếu lỗi
            return {"error": str(e)}

    def restart_browser(self):
        """Safely restart the browser session"""
        self._shutdown_browser()
        self._init_browser()

# ----------------------------------------------------------------------
#                        MAIN FLASK APP
# ----------------------------------------------------------------------


app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False
browser_worker = None

# --- BỔ SUNG: Hàm xác thực ---


def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key_from_header = request.headers.get('X-API-KEY')
        # Kiểm tra Key từ header với Key trong config
        if key_from_header and key_from_header == API_TOKEN:
            return f(*args, **kwargs)
        else:
            return jsonify({'error': 'Unauthorized: Invalid or missing API Key'}), 401
    return decorated_function


@app.route('/chat', methods=['POST'])
@require_api_key
def chat_endpoint():
    data = request.get_json()
    if not data or 'message' not in data:
        return Response(
            json.dumps({'error': 'Missing message'}, ensure_ascii=False),
            mimetype='application/json'
        ), 400

    message = data['message']

    result_queue = queue.Queue()

    browser_worker.task_queue.put({
        'type': 'chat',
        'message': message,
        'result_queue': result_queue
    })

    try:
        result = result_queue.get(timeout=120)
        if 'error' in result:
            return Response(
                json.dumps(result, ensure_ascii=False),
                mimetype='application/json'
            ), 500

        return Response(
            json.dumps(result, ensure_ascii=False),
            mimetype='application/json'
        )
    except queue.Empty:
        return Response(
            json.dumps({'error': 'Server busy or timeout'},
                       ensure_ascii=False),
            mimetype='application/json'
        ), 504


@app.route('/health', methods=['GET'])
def health():
    status = "ready" if browser_worker.ready else "idle"
    return jsonify({'status': status})

@app.route('/restart', methods=['POST'])
@require_api_key
def restart_browser_endpoint():
    try:
        browser_worker.restart_browser()
        return jsonify({'status': 'Browser restarted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def signal_handler(sig, frame):
    print("\nShutting down server...")
    if browser_worker:
        browser_worker.task_queue.put({'type': 'shutdown_app'})
        browser_worker.join(timeout=5)
    exit(0)


if __name__ == "__main__":
    import signal
    from waitress import serve

    signal.signal(signal.SIGINT, signal_handler)

    # Start Worker Thread
    browser_worker = BrowserWorker()
    browser_worker.start()

    print(
        f"Server running on port 5001. Session timeout: {SESSION_TIMEOUT_MINUTES} minutes")
    # --- BỔ SUNG: In key ra màn hình ---
    print(f"Auth Enabled. Key: {API_TOKEN}")

    # Serve Flask app via Waitress (production)
    serve(app, host='0.0.0.0', port=5001, threads=1)
