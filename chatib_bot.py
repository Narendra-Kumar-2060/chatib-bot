from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
from flask import Flask
import threading
import time
import random
import string

# ---------- Configuration ----------
SITE_URL = "https://www.chatib.us"
ROOM_URL = "https://www.chatibrooms.com/user/chatroom/philosophy-chat-room"
TOKEN_URL = "https://www.chatib.us/auth/generateSsoToken/philosophy-chat-room"
WAIT_TIMEOUT = 30
app = Flask(__name__)


# ---------- Helper Functions ----------
def generate_letter_string(length=6):
    return "".join(random.choices(string.ascii_letters, k=length))


def setup_driver():
    """Headless Chrome driver using manually uploaded ChromeDriver."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-features=NetworkService")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Use the manually uploaded driver
    service = Service(executable_path="/app/drivers/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def send_message(driver, text):
    try:
        input_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#contenteditablediv"))
        )
        input_box.click()
        input_box.clear()
        input_box.send_keys(text)
        send_btn = driver.find_element(By.CSS_SELECTOR, ".msg_send_btn")
        send_btn.click()
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f"⚠️ Failed to send message: {e}")
        return False


def login(driver, wait):
    print("\n--- Logging in ---")
    random_username = generate_letter_string(6)
    random_number = random.randint(1000, 9999)
    full_username = f"LemonTree{random_number}"

    try:
        username_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#username"))
        )
        username_field.send_keys(full_username)
        print("✅ Username entered")
    except TimeoutException:
        print("❌ Username field not found.")
        raise

    try:
        gender = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".checkmark-male"))
        )
        gender.click()
        print("✅ Gender selected")
    except TimeoutException:
        raise

    try:
        age_select = Select(
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#age")))
        )
        age_select.select_by_visible_text("24")
        print("✅ Age selected")
    except TimeoutException:
        raise

    try:
        country_select = Select(
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#login_country"))
            )
        )
        country_select.select_by_visible_text("United States")
        print("✅ Country selected")
    except TimeoutException:
        raise

    time.sleep(2)
    try:
        city_select = Select(
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#city")))
        )
        try:
            city_select.select_by_visible_text("New York")
        except:
            if len(city_select.options) > 1:
                city_select.select_by_index(1)
                print(
                    f"✅ City selected (fallback): {city_select.first_selected_option.text}"
                )
    except TimeoutException:
        raise

    try:
        start_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#startChatNow"))
        )
        start_btn.click()
        print("✅ Start button clicked")
    except TimeoutException:
        raise

    time.sleep(2)
    try:
        accept_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".btn.btn-primary.confirm_decline.agree")
            )
        )
        accept_btn.click()
        print("✅ TOS popup accepted")
    except:
        print("⚠️ TOS popup not found – continuing.")

    print("✅ Login complete.")
    return full_username


def navigate_to_room(driver, wait):
    print("\n--- Navigating to room ---")
    try:
        driver.get(TOKEN_URL)
        print("✅ Token endpoint visited")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Failed to load token endpoint: {e}")
        raise

    if "chatibrooms" not in driver.current_url:
        try:
            driver.get(ROOM_URL)
            print("✅ Room URL loaded")
        except Exception as e:
            print(f"❌ Failed to load room URL: {e}")
            raise
    else:
        print("✅ Already on room page.")

    try:
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".received_withd_msg"))
        )
        print("✅ Room messages detected.")
    except TimeoutException:
        print("⚠️ No messages yet, but room may be loading.")

    print(f"📍 Final URL: {driver.current_url}")
    return driver.current_url


def parse_message(raw):
    lines = raw.splitlines()
    username_line = None
    for line in lines:
        if "| report |" in line:
            username_line = line
            break
    if username_line:
        user = username_line.split("|")[0].strip()
        msg_lines = [l for l in lines if l != username_line]
        msg = " ".join(msg_lines).strip()
        return user, msg
    return None, raw


def monitor_and_play(driver, bot_username):
    print("\n--- Game monitor started (Ctrl+C to stop) ---")
    target = random.randint(1, 100)
    game_active = True
    print(f"🎯 (DEBUG) Target: {target}")

    send_message(
        driver,
        "I'm thinking of a number between 1 and 100.",
    )

    seen = set()
    poll_interval = 2

    try:
        while True:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, ".received_withd_msg")
                for elem in elements:
                    raw = elem.text.strip()
                    if not raw:
                        continue

                    user, msg = parse_message(raw)
                    if user == bot_username:
                        continue
                    if not msg.lower().startswith("!guess"):
                        continue

                    key = (user, msg)
                    if key in seen:
                        continue
                    seen.add(key)

                    parts = msg.split()
                    if len(parts) != 2:
                        send_message(driver, f"{user}, use: !guess [number]")
                        continue

                    try:
                        guess = int(parts[1])
                    except ValueError:
                        send_message(
                            driver, f"{user}, please provide a valid number."
                        )
                        continue

                    if not game_active:
                        send_message(
                            driver, "A new round has started!"
                        )
                        continue

                    if guess == target:
                        reply = (
                            f"Correct, {user}! The number was {target}. New round!"
                        )
                        send_message(driver, reply)
                        target = random.randint(1, 100)
                        game_active = True
                        seen.clear()
                        print(f"🎯 (DEBUG) New target: {target}")
                        send_message(
                            driver,
                            "I'm thinking of a new number between 1 and 100.",
                        )
                    elif guess < target:
                        send_message(driver, f"Too low, {user}!")
                    else:
                        send_message(driver, f"Too high, {user}!")

                time.sleep(poll_interval)

            except Exception as e:
                print(f"⚠️ Error in monitor loop: {e}")
                time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n🛑 Game monitor stopped.")


def main():
    while True:
        driver = None
        try:
            print("🔄 Setting up driver...")
            driver = setup_driver()
            print("✅ Driver ready")
            wait = WebDriverWait(driver, WAIT_TIMEOUT)

            driver.get(SITE_URL)
            print("📄 Main page loaded")

            username = login(driver, wait)
            final_url = navigate_to_room(driver, wait)

            if "chatibrooms" in final_url:
                monitor_and_play(driver, username)
            else:
                print(f"⚠️ Not on room page – retrying...")

            print("\n" + "=" * 50)
            print("✅ SESSION COMPLETE!")
            print(f"👤 Username: {username}")
            print("=" * 50)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(10)

        finally:
            if driver:
                driver.quit()
            print("🔄 Restarting in 10 seconds...")
            time.sleep(10)


@app.route('/')
def home():
    return "Chatib Bot is running!"


if __name__ == "__main__":
    import sys

    def run_bot():
        try:
            print("🚀 Bot thread started")
            main()
        except Exception as e:
            print(f"❌ Bot thread crashed: {e}")
            import traceback
            traceback.print_exc()

    # Start the bot in a background thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    print("✅ Bot thread launched")

    # Run the web server
    app.run(host='0.0.0.0', port=8080)