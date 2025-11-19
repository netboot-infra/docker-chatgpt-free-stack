# File: apigpt.py

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import sys
import os
import random
import math
from threading import Thread, Lock
from flask import Flask, request, jsonify

# --- HÀM MÔ PHỎNG HÀNH VI CON NGƯỜI (GIỮ NGUYÊN) ---


def simulate_human_mouse_movement(page, start_x, start_y, end_x, end_y, duration=1.0):
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
    current_pos = (random.randint(0, 1920), random.randint(
        0, 1080))
    simulate_human_mouse_movement(
        page, current_pos[0], current_pos[1], x, y, random.uniform(0.5, 1.5))
    time.sleep(random.uniform(0.1, 0.3))
    click_x = x + random.randint(-2, 2)
    click_y = y + random.randint(-2, 2)
    page.mouse.click(click_x, click_y)
    time.sleep(random.uniform(0.1, 0.2))


def simulate_human_typing(page, selector, text):
    page.click(selector)
    time.sleep(random.uniform(0.2, 0.5))
    typed_text = ""
    for char in text:
        if random.random() < 0.02:
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            page.type(selector, wrong_char)
            typed_text += wrong_char
            time.sleep(random.uniform(0.1, 0.3))
            page.press(selector, "Backspace")
            typed_text = typed_text[:-1]
            time.sleep(random.uniform(0.1, 0.2))

        page.type(selector, char)
        typed_text += char
        if char == " ":
            time.sleep(random.uniform(0.1, 0.3))
        elif char in ",.!?:;":
            time.sleep(random.uniform(0.2, 0.4))
        else:
            time.sleep(random.uniform(0.05, 0.2))
    return typed_text


# --- GLOBAL VARIABLES VÀ CÀI ĐẶT THỜI GIAN SỐNG ---
browser_instance = None
page_instance = None
chatgpt_ready = False
playwright_instance = None
context_instance = None
lock = Lock()  # Khóa luồng cho các thao tác Playwright

# 💡 BIẾN CÀI ĐẶT THỜI GIAN SỐNG (ĐƠN VỊ: PHÚT)
SESSION_TIMEOUT_MINUTES = 10
# Tính toán thời gian chờ đóng (đơn vị: giây)
SHUTDOWN_TIMEOUT = SESSION_TIMEOUT_MINUTES * 60

last_activity_time = 0.0  # Timestamp của lần hoạt động cuối cùng

# --- HÀM DỌN DẸP ---


def shutdown_chatgpt():
    """Đóng trình duyệt và giải phóng tài nguyên Playwright."""
    global browser_instance, page_instance, chatgpt_ready, playwright_instance, context_instance, last_activity_time

    with lock:
        if chatgpt_ready:
            print(
                f"--- Đã quá {SESSION_TIMEOUT_MINUTES} phút không hoạt động. Đang đóng trình duyệt ChatGPT. ---")
            try:
                if browser_instance:
                    browser_instance.close()
                if playwright_instance:
                    playwright_instance.stop()
            except Exception as e:
                print(f"Lỗi khi đóng trình duyệt: {e}")

            browser_instance = None
            page_instance = None
            context_instance = None
            playwright_instance = None
            chatgpt_ready = False
            last_activity_time = 0.0

# --- HÀM KHỞI TẠO ON-DEMAND ---


def initialize_chatgpt(debugBrowser=False):
    """Khởi tạo kết nối ChatGPT nếu chưa sẵn sàng."""
    global browser_instance, page_instance, chatgpt_ready, playwright_instance, context_instance, last_activity_time

    if chatgpt_ready:
        return True

    with lock:
        if chatgpt_ready:
            return True

        print("--- Không tìm thấy kết nối. Đang khởi tạo ChatGPT... ---")
        try:
            playwright_instance = sync_playwright().start()

            browser_instance = playwright_instance.chromium.launch(
                headless=not debugBrowser,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                    "--disable-infobars",
                    "--disable-extensions",
                ]
            )

            context_instance = browser_instance.new_context(
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

            page_instance = context_instance.new_page()

            stealth = Stealth()
            stealth.apply_stealth_sync(page_instance)

            print("Accessing https://chatgpt.com ...")
            page_instance.goto("https://chatgpt.com", timeout=60000)
            page_instance.wait_for_load_state("domcontentloaded")
            time.sleep(5)

            chatgpt_ready = True
            last_activity_time = time.time()  # Ghi lại thời điểm khởi tạo
            print(
                f"--- KHỞI TẠO THÀNH CÔNG! Thời gian chờ là {SESSION_TIMEOUT_MINUTES} phút. ---")
            return True

        except Exception as e:
            print(f"Error initializing ChatGPT: {e}")
            shutdown_chatgpt()
            return False

# --- HÀM GỬI TIN NHẮN (CẬP NHẬT THỜI GIAN) ---


def send_message_to_chatgpt(message):
    """Gửi tin nhắn và cập nhật thời gian hoạt động."""
    global last_activity_time

    if not initialize_chatgpt(debugBrowser=False):
        return "ChatGPT không thể khởi tạo. Vui lòng kiểm tra lỗi."

    with lock:
        try:
            # Xử lý login/guest prompt (Giữ nguyên)
            try:
                login_prompt = page_instance.query_selector(
                    'div.flex.flex-col.items-center.justify-center.px-6.py-8')
                if login_prompt:
                    continue_as_guest = login_prompt.query_selector(
                        'a.cursor-pointer')
                    if continue_as_guest:
                        print("Skipping login prompt...")
                        bbox = continue_as_guest.bounding_box()
                        if bbox:
                            center_x = bbox['x'] + bbox['width'] / 2
                            center_y = bbox['y'] + bbox['height'] / 2
                            simulate_human_click(
                                page_instance, center_x, center_y)
                        else:
                            continue_as_guest.click()
                        time.sleep(2)
            except:
                pass

            # Gửi tin nhắn và chờ phản hồi (Giữ nguyên)
            try:
                page_instance.wait_for_selector(
                    'div.ProseMirror#prompt-textarea', timeout=5000)
                simulate_human_typing(
                    page_instance, 'div.ProseMirror#prompt-textarea', message)
                send_button = page_instance.query_selector(
                    'button[data-testid="send-button"]')
                if send_button:
                    bbox = send_button.bounding_box()
                    if bbox:
                        center_x = bbox['x'] + bbox['width'] / 2
                        center_y = bbox['y'] + bbox['height'] / 2
                        simulate_human_click(page_instance, center_x, center_y)
                    else:
                        send_button.click()
                else:
                    time.sleep(random.uniform(0.2, 0.5))
                    page_instance.press(
                        'div.ProseMirror#prompt-textarea', 'Enter')

                # ... (Code chờ phản hồi) ...
                response_started = False
                start_time = time.time()
                timeout = 30
                try:
                    page_instance.wait_for_selector(
                        'button[data-testid="stop-button"]', timeout=5000)
                    response_started = True
                    while response_started and (time.time() - start_time) < timeout:
                        try:
                            stop_button = page_instance.query_selector(
                                'button[data-testid="stop-button"]')
                            if stop_button is None:
                                response_started = False
                                break
                            time.sleep(0.1)
                        except:
                            response_started = False
                            break
                except:
                    time.sleep(2)

                try:
                    page_instance.wait_for_selector(
                        'div.markdown.prose', timeout=10000)
                    time.sleep(0.5)

                    response_elements = page_instance.query_selector_all(
                        'div.markdown.prose')

                    if response_elements:
                        latest_response = response_elements[-1]
                        response_text = latest_response.inner_text()
                    else:
                        response_text = "Could not find response from ChatGPT."

                    # 💡 CẬP NHẬT THỜI GIAN HOẠT ĐỘNG CUỐI CÙNG
                    last_activity_time = time.time()
                    return response_text

                except Exception as response_error:
                    return f"Could not extract response: {response_error}"

            except Exception as e:
                return f"Error sending question: {e}"

        except Exception as e:
            return f"Error communicating with ChatGPT: {e}"


# --- HÀM THEO DÕI THỜI GIAN ---
def background_timeout_checker():
    """Luồng nền kiểm tra thời gian không hoạt động và tự động đóng trình duyệt."""
    while True:
        time.sleep(5)  # Kiểm tra mỗi 5 giây

        global last_activity_time, chatgpt_ready, SHUTDOWN_TIMEOUT

        # 💡 TÍNH TOÁN LẠI SHUTDOWN_TIMEOUT TRONG VÒNG LẶP (nếu bạn muốn thay đổi runtime)
        # Nếu không cần thay đổi runtime, bạn có thể bỏ qua dòng này và chỉ dùng SHUTDOWN_TIMEOUT cố định.
        current_shutdown_timeout = SESSION_TIMEOUT_MINUTES * 60

        if chatgpt_ready and last_activity_time > 0:
            elapsed_time = time.time() - last_activity_time
            if elapsed_time > current_shutdown_timeout:
                shutdown_chatgpt()


# --- KHỞI TẠO FLASK APP VÀ ENDPOINT ---
app = Flask(__name__)


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Missing message in request body'}), 400

        message = data['message']
        response = send_message_to_chatgpt(message)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ready' if chatgpt_ready else 'idle/initializing'})


if __name__ == "__main__":
    # KHỞI TẠO LUỒNG KIỂM TRA THỜI GIAN
    checker_thread = Thread(target=background_timeout_checker, daemon=True)
    checker_thread.start()

    print(
        f"Server khởi động. Thời gian chờ hiện tại: {SESSION_TIMEOUT_MINUTES} phút.")
    # Chạy Flask ở chế độ đơn luồng
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=False)
