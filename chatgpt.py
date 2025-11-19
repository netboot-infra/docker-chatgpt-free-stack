# File: chatgpt_opener.py
# Run with: python chatgpt_opener.py

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import sys
import os
import random
import math


def simulate_human_mouse_movement(page, start_x, start_y, end_x, end_y, duration=1.0):
    """Simulate human-like mouse movement with slight deviations and varying speed"""
    # Add some randomness to the path
    num_points = random.randint(10, 20)
    points = []

    # Generate intermediate points with slight deviations
    for i in range(num_points + 1):
        t = i / num_points
        # Linear interpolation with noise
        x = start_x + (end_x - start_x) * t + random.randint(-20, 20)
        y = start_y + (end_y - start_y) * t + random.randint(-20, 20)
        points.append((x, y))

    # Move mouse through points with varying timing
    for i, (x, y) in enumerate(points):
        page.mouse.move(x, y)
        # Vary the delay between movements to simulate human-like timing
        time.sleep(random.uniform(0.01, duration/len(points)))


def simulate_human_click(page, x, y):
    """Simulate human-like clicking with slight delays and positioning variations"""
    # Move to the position with human-like movement
    current_pos = (random.randint(0, 1920), random.randint(
        0, 1080))  # Simulate current mouse position
    simulate_human_mouse_movement(
        page, current_pos[0], current_pos[1], x, y, random.uniform(0.5, 1.5))

    # Add small pause before clicking
    time.sleep(random.uniform(0.1, 0.3))

    # Slight variation in click position
    click_x = x + random.randint(-2, 2)
    click_y = y + random.randint(-2, 2)

    # Perform the click
    page.mouse.click(click_x, click_y)

    # Small pause after clicking
    time.sleep(random.uniform(0.1, 0.2))


def simulate_human_typing(page, selector, text):
    """Simulate human-like typing with varying speeds and occasional mistakes"""
    # Focus on the element first
    page.click(selector)
    time.sleep(random.uniform(0.2, 0.5))

    typed_text = ""
    for char in text:
        # Occasionally make mistakes (but immediately correct them)
        if random.random() < 0.02:  # 2% chance of making a mistake
            # Type a wrong character
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            page.type(selector, wrong_char)
            typed_text += wrong_char
            time.sleep(random.uniform(0.1, 0.3))

            # Backspace to correct
            page.press(selector, "Backspace")
            typed_text = typed_text[:-1]
            time.sleep(random.uniform(0.1, 0.2))

        # Type the correct character
        page.type(selector, char)
        typed_text += char

        # Vary typing speed
        if char == " ":
            time.sleep(random.uniform(0.1, 0.3))  # Longer pause for spaces
        elif char in ",.!?:;":
            # Longer pause for punctuation
            time.sleep(random.uniform(0.2, 0.4))
        else:
            time.sleep(random.uniform(0.05, 0.2))  # Regular typing speed

    return typed_text


def open_chatgpt(debugBrowser=False):
    with sync_playwright() as p:
        if debugBrowser:
            print("Starting Chromium...")
        else:
            print("Starting Chromium in headless mode...")

        browser = p.chromium.launch(
            headless=not debugBrowser,           # True = run headless, False = show browser
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--disable-infobars",
                "--disable-extensions",
            ]
        )

        # Create context that looks like a real user
        context = browser.new_context(
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

        page = context.new_page()

        # Apply stealth - required to avoid being blocked by OpenAI/Cloudflare
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        print("Accessing https://chatgpt.com ...")
        page.goto("https://chatgpt.com", timeout=60000)

        # Wait for page to fully load
        page.wait_for_load_state("domcontentloaded")
        # Additional wait (OpenAI sometimes loads slowly)
        time.sleep(5)

        # Start a background thread for random mouse movements
        if debugBrowser:
            import threading
            # Track current mouse position
            current_mouse_pos = [960, 540]  # Start at center

            def background_behaviors():
                try:
                    while True:
                        # 70% chance of mouse movement, 30% chance of scrolling
                        if random.random() < 0.7:
                            # Generate random coordinates within the viewport
                            x = random.randint(50, 1870)
                            y = random.randint(50, 1030)

                            # Move mouse to random position with human-like movement
                            simulate_human_mouse_movement(
                                page, current_mouse_pos[0], current_mouse_pos[1], x, y, random.uniform(0.5, 2.0))
                            current_mouse_pos[0], current_mouse_pos[1] = x, y
                        else:
                            # Random scrolling behavior
                            scroll_amount = random.randint(-100, 100)
                            page.mouse.wheel(0, scroll_amount)

                        # Random pause
                        time.sleep(random.uniform(1, 5))
                except:
                    pass  # Stop when program ends

            # Start the background thread
            behavior_thread = threading.Thread(
                target=background_behaviors, daemon=True)
            behavior_thread.start()

        if debugBrowser:
            print("=====================================================================")
            print("SUCCESSFULLY OPENED CHATGPT!")
            print("You can log in and use it normally in the browser window.")
            print("Type 'exit' or 'quit' to close the program.")
            print("Type 'clear' to clear the console.")
            print("Type 'restart' to restart the application.")
            print("=====================================================================")
        else:
            print("=====================================================================")
            print("SUCCESSFULLY CONNECTED TO CHATGPT!")
            print("Type 'exit' or 'quit' to close the program.")
            print("Type 'clear' to clear the console.")
            print("Type 'restart' to restart the application.")
            print("=====================================================================")

        # Keep browser open until user presses Ctrl+C
        try:
            while True:
                # Get user input from console
                user_input = input("you: ")

                # Check if user wants to exit
                if user_input.lower() in ['exit', 'quit']:
                    break

                # Check if user wants to restart the application
                if user_input.lower() == 'restart':
                    print("Restarting application...")
                    browser.close()
                    # Restart the application by re-executing the script
                    python = sys.executable
                    os.execl(python, python, *sys.argv)

                # Check if user wants to clear console
                if user_input.lower() == 'clear':
                    # Clear console based on OS
                    if os.name == 'nt':  # Windows
                        os.system('cls')
                    else:  # Unix/Linux/Mac
                        os.system('clear')
                    continue

                # Skip empty inputs
                if not user_input.strip():
                    continue

                # Check for login/signup prompt and handle it
                try:
                    login_prompt = page.query_selector(
                        'div.flex.flex-col.items-center.justify-center.px-6.py-8')
                    if login_prompt:
                        # Look for the "Continue as guest" link
                        continue_as_guest = login_prompt.query_selector(
                            'a.cursor-pointer')
                        if continue_as_guest:
                            if debugBrowser:
                                print("Skipping login prompt...")
                            # Get the bounding box for human-like clicking
                            bbox = continue_as_guest.bounding_box()
                            if bbox:
                                center_x = bbox['x'] + bbox['width'] / 2
                                center_y = bbox['y'] + bbox['height'] / 2
                                simulate_human_click(page, center_x, center_y)
                            else:
                                # Fallback if we can't get bounding box
                                continue_as_guest.click()
                            # Wait a bit for the prompt to disappear
                            time.sleep(2)
                except:
                    pass  # If we can't handle the login prompt, continue anyway

                # Send the user input to ChatGPT textarea
                try:
                    # Wait for the textarea to be available
                    page.wait_for_selector(
                        'div.ProseMirror#prompt-textarea', timeout=5000)

                    # Fill the textarea with user input using human-like typing
                    simulate_human_typing(
                        page, 'div.ProseMirror#prompt-textarea', user_input)

                    # Click the send button instead of pressing enter
                    # First, try to find and click the send button with human-like behavior
                    send_button = page.query_selector(
                        'button[data-testid="send-button"]')
                    if send_button:
                        # Get button bounding box for precise clicking
                        bbox = send_button.bounding_box()
                        if bbox:
                            center_x = bbox['x'] + bbox['width'] / 2
                            center_y = bbox['y'] + bbox['height'] / 2
                            simulate_human_click(page, center_x, center_y)
                        else:
                            # Fallback if we can't get bounding box
                            send_button.click()
                    else:
                        # Fallback: try pressing Enter with a human-like pause
                        time.sleep(random.uniform(0.2, 0.5))
                        page.press('div.ProseMirror#prompt-textarea', 'Enter')

                    # Show loading indicator with animation
                    print("gpt: ", end="", flush=True)
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
                            'button[data-testid="stop-button"]', timeout=5000)  # Reduced from 10000 to 5000 ms
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
                                print(
                                    f"\rgpt: {loading_chars[loading_index % len(loading_chars)]}", end="", flush=True)
                                loading_index += 1
                                time.sleep(0.1)
                            except:
                                response_started = False
                                break

                        # Clear loading animation
                        print("\rgpt: ", end="", flush=True)
                    except:
                        # If we can't detect the stop button, show simple loading
                        time.sleep(2)  # Reduced from 3 to 2 seconds

                    # Try to extract the latest response
                    try:
                        # Wait for response elements to appear
                        page.wait_for_selector(
                            'div.markdown.prose', timeout=10000)

                        # Reduce the wait time for the text to fully render
                        # Reduced from 2 seconds to 0.5 seconds
                        time.sleep(0.5)

                        # Get all response elements
                        response_elements = page.query_selector_all(
                            'div.markdown.prose')

                        if response_elements:
                            # Get the last response (most recent one)
                            latest_response = response_elements[-1]
                            response_text = latest_response.inner_text()
                            print(response_text)
                        else:
                            print("Could not find response from ChatGPT.")

                    except Exception as response_error:
                        print(f"Could not extract response: {response_error}")

                except Exception as e:
                    print(f"Error sending question: {e}")

        except KeyboardInterrupt:
            print("\nClosing browser... Bye!")
        finally:
            browser.close()


if __name__ == "__main__":
    # Set debugBrowser=True to show browser, False to run headless
    debugBrowser = False  # Change this to True if you want to see the browser
    open_chatgpt(debugBrowser)
