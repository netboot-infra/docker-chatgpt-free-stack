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
from flask import Flask, request, jsonify

# ----------------------------------------------------------------------
#                          CẤU HÌNH
# ----------------------------------------------------------------------
SESSION_TIMEOUT_MINUTES = 2  # Tăng lên 2 phút để đỡ phải login lại nhiều
SHUTDOWN_TIMEOUT = SESSION_TIMEOUT_MINUTES * 60
HEADLESS_MODE = False        # Đặt True nếu chạy trên server không màn hình

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
    time.sleep(random.uniform(0.2, 0.5))
    typed_text = ""
    for char in text:
        if random.random() < 0.02:  # 2% chance of typo
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

# ----------------------------------------------------------------------
#                     BROWSER WORKER (THE CORE FIX)
# ----------------------------------------------------------------------
# Lớp này chạy trên 1 luồng riêng biệt. Flask chỉ gửi task vào đây.


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

    def run(self):
        print("--- Browser Worker Thread Started ---")
        while self.is_running:
            try:
                # Chờ task tối đa 1 giây, sau đó kiểm tra timeout
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
                print(f"Lỗi Fatal trong Worker Loop: {e}")

    def _check_idle_timeout(self):
        """Kiểm tra nếu không hoạt động quá lâu thì đóng trình duyệt"""
        if self.ready and (time.time() - self.last_activity > SHUTDOWN_TIMEOUT):
            print(
                f"--- Timeout {SESSION_TIMEOUT_MINUTES}p. Đóng trình duyệt để giải phóng RAM. ---")
            self._shutdown_browser()

    def _init_browser(self):
        """Khởi tạo Playwright (Chỉ chạy trong Worker Thread)"""
        if self.ready:
            return True

        print("--- Đang khởi tạo ChatGPT Browser... ---")
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=HEADLESS_MODE,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                ]
            )

            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )

            self.page = self.context.new_page()
            stealth = Stealth()
            stealth.apply_stealth_sync(self.page)

            print("Truy cập https://chatgpt.com ...")
            self.page.goto("https://chatgpt.com", timeout=60000)

            # Xử lý login Guest nếu có
            try:
                guest_btn = self.page.query_selector(
                    'div.flex.flex-col.items-center.justify-center >> text=Stay logged out')
                # Note: Selector guest thay đổi liên tục, dùng try/catch lỏng
                if not guest_btn:
                    # Thử tìm nút "Start chatting" hoặc tương tự
                    pass
            except:
                pass

            time.sleep(3)
            self.ready = True
            self.last_activity = time.time()
            print("--- Khởi tạo thành công ---")
            return True
        except Exception as e:
            print(f"Lỗi khởi tạo: {e}")
            self._shutdown_browser()
            return False

    def _shutdown_browser(self):
        """Đóng trình duyệt an toàn"""
        print("--- Đang đóng trình duyệt... ---")
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

    def _process_chat(self, message):
        """Xử lý logic chat"""
        self.last_activity = time.time()

        # 1. Đảm bảo browser đã mở
        if not self._init_browser():
            return {"error": "Không thể khởi tạo trình duyệt"}

        try:
            page = self.page

            # --- XỬ LÝ TEXTAREA ---
            # Tăng timeout lên 10s
            try:
                textarea = page.wait_for_selector(
                    'div.ProseMirror#prompt-textarea', state='visible', timeout=10000)
                if not textarea:
                    raise Exception("Không tìm thấy ô nhập liệu")
            except:
                # Fallback: Đôi khi class thay đổi, thử click vào body rồi tìm lại
                page.mouse.click(500, 500)
                textarea = page.wait_for_selector(
                    '#prompt-textarea', state='visible', timeout=5000)

            simulate_human_typing(
                page, 'div.ProseMirror#prompt-textarea', message)

            # Click gửi
            send_btn = page.query_selector('button[data-testid="send-button"]')
            if send_btn:
                send_btn.click()
            else:
                page.keyboard.press("Enter")

            # --- CHỜ VÀ LẤY PHẢN HỒI ---
            # Logic: Chờ nút Stop xuất hiện (đang gen) -> Chờ nút Stop biến mất (đã gen xong)
            try:
                page.wait_for_selector(
                    'button[data-testid="stop-button"]', timeout=5000)
            except:
                pass  # Có thể nó gen quá nhanh

            # Chờ nút Copy hoặc nút Regenerate xuất hiện (dấu hiệu xong)
            # Hoặc đơn giản là đợi div markdown prose ổn định
            time.sleep(2)

            # Tăng timeout chờ phản hồi lên 30s
            try:
                page.wait_for_selector('div.markdown.prose', timeout=30000)
            except:
                return {"error": "Timeout khi chờ phản hồi từ ChatGPT"}

            # Đợi thêm chút để render hết
            timeout_count = 0
            prev_len = 0
            while timeout_count < 30:  # Đợi tối đa 30s cho việc generate text dài
                responses = page.query_selector_all('div.markdown.prose')
                if not responses:
                    break
                current_text = responses[-1].inner_text()
                if len(current_text) > prev_len:
                    prev_len = len(current_text)
                    timeout_count = 0  # Reset nếu text vẫn đang dài ra
                    time.sleep(1)
                else:
                    # Text không đổi trong 1s -> Có thể đã xong
                    timeout_count += 1
                    if timeout_count > 2:
                        break

            final_responses = page.query_selector_all('div.markdown.prose')
            if final_responses:
                return {"response": final_responses[-1].inner_text()}
            else:
                return {"error": "Không lấy được nội dung phản hồi"}

        except Exception as e:
            print(f"Lỗi trong quá trình chat: {e}")
            self._shutdown_browser()  # Reset nếu lỗi
            return {"error": str(e)}

# ----------------------------------------------------------------------
#                        MAIN FLASK APP
# ----------------------------------------------------------------------


app = Flask(__name__)
browser_worker = None


@app.route('/chat', methods=['POST'])
def chat_endpoint():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Missing message'}), 400

    message = data['message']

    # Cơ chế giao tiếp Thread-safe:
    # 1. Tạo hàng đợi kết quả riêng cho request này
    result_queue = queue.Queue()

    # 2. Gửi task sang Worker Thread
    browser_worker.task_queue.put({
        'type': 'chat',
        'message': message,
        'result_queue': result_queue
    })

    # 3. Chờ kết quả (Block request này cho đến khi Worker trả lời)
    try:
        # Timeout tổng 120s cho cả quá trình
        result = result_queue.get(timeout=120)
        if 'error' in result:
            return jsonify(result), 500
        return jsonify(result)
    except queue.Empty:
        return jsonify({'error': 'Server busy or timeout'}), 504


@app.route('/health', methods=['GET'])
def health():
    status = "ready" if browser_worker.ready else "idle"
    return jsonify({'status': status})


def signal_handler(sig, frame):
    print("\nĐang tắt server...")
    if browser_worker:
        browser_worker.task_queue.put({'type': 'shutdown_app'})
        browser_worker.join(timeout=5)
    exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    # Khởi chạy Worker Thread
    browser_worker = BrowserWorker()
    browser_worker.start()

    print(
        f"Server chạy port 5001. Timeout phiên: {SESSION_TIMEOUT_MINUTES} phút")
    # Threaded=True ok vì Browser logic đã tách biệt hoàn toàn
    app.run(host='0.0.0.0', port=5001, threaded=True)
