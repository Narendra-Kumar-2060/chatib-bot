from playwright.sync_api import sync_playwright
from flask import Flask
import threading
import time
import random
import string

app = Flask(__name__)

# ---------- Configuration ----------
SITE_URL = "https://www.chatib.us"
ROOM_URL = "https://www.chatibrooms.com/user/chatroom/philosophy-chat-room"
TOKEN_URL = "https://www.chatib.us/auth/generateSsoToken/philosophy-chat-room"
WAIT_TIMEOUT = 30

def generate_letter_string(length=6):
    return "".join(random.choices(string.ascii_letters, k=length))

def send_message(page, text):
    try:
        page.fill("#contenteditablediv", text)
        page.click(".msg_send_btn")
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f"⚠️ Failed to send message: {e}")
        return False

def login(page):
    print("\n--- Logging in ---")
    random_username = generate_letter_string(6)
    random_number = random.randint(1000, 9999)
    full_username = f"LemonTree{random_number}"

    try:
        page.fill("#username", full_username)
        print("✅ Username entered")
    except:
        print("❌ Username field not found.")
        raise

    try:
        page.click(".checkmark-male")
        print("✅ Gender selected")
    except:
        raise

    try:
        page.select_option("#age", "24")
        print("✅ Age selected")
    except:
        raise

    try:
        page.select_option("#login_country", "United States")
        print("✅ Country selected")
    except:
        raise

    time.sleep(2)
    try:
        page.select_option("#city", "New York")
        print("✅ City selected")
    except:
        print("⚠️ City not found, using first available")
        page.select_option("#city", index=1)

    try:
        page.click("#startChatNow")
        print("✅ Start button clicked")
    except:
        raise

    time.sleep(2)
    try:
        page.click(".btn.btn-primary.confirm_decline.agree")
        print("✅ TOS popup accepted")
    except:
        print("⚠️ TOS popup not found – continuing.")

    print("✅ Login complete.")
    return full_username

def navigate_to_room(page):
    print("\n--- Navigating to room ---")
    try:
        page.goto(TOKEN_URL)
        print("✅ Token endpoint visited")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Failed to load token endpoint: {e}")
        raise

    if "chatibrooms" not in page.url:
        try:
            page.goto(ROOM_URL)
            print("✅ Room URL loaded")
        except Exception as e:
            print(f"❌ Failed to load room URL: {e}")
            raise
    else:
        print("✅ Already on room page.")

    try:
        page.wait_for_selector(".received_withd_msg", timeout=WAIT_TIMEOUT*1000)
        print("✅ Room messages detected.")
    except:
        print("⚠️ No messages yet, but room may be loading.")

    print(f"📍 Final URL: {page.url}")
    return page.url

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

def monitor_and_play(page, bot_username):
    print("\n--- Game monitor started ---")
    target = random.randint(1, 100)
    print(f"🎯 (DEBUG) Target: {target}")

    send_message(page, "I'm thinking of a number between 1 and 100.")

    seen = set()
    poll_interval = 2

    while True:
        try:
            elements = page.query_selector_all(".received_withd_msg")
            for elem in elements:
                raw = elem.inner_text().strip()
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
                    send_message(page, f"{user}, use: !guess [number]")
                    continue

                try:
                    guess = int(parts[1])
                except ValueError:
                    send_message(page, f"{user}, please provide a valid number.")
                    continue

                if guess == target:
                    reply = f"Correct, {user}! The number was {target}. New round!"
                    send_message(page, reply)
                    target = random.randint(1, 100)
                    seen.clear()
                    print(f"🎯 (DEBUG) New target: {target}")
                    send_message(page, "I'm thinking of a new number between 1 and 100.")
                elif guess < target:
                    send_message(page, f"Too low, {user}!")
                else:
                    send_message(page, f"Too high, {user}!")

            time.sleep(poll_interval)

        except Exception as e:
            print(f"⚠️ Error in monitor loop: {e}")
            time.sleep(poll_interval)

def main():
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                page = browser.new_page()
                print("✅ Browser launched")

                page.goto(SITE_URL)
                print("📄 Main page loaded")

                username = login(page)
                final_url = navigate_to_room(page)

                if "chatibrooms" in final_url:
                    monitor_and_play(page, username)
                else:
                    print(f"⚠️ Not on room page – retrying...")

                browser.close()
                print("🔄 Session ended, restarting...")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            time.sleep(10)

        time.sleep(5)

@app.route('/')
def home():
    return "Chatib Bot is running!"

if __name__ == "__main__":
    def run_bot():
        print("🚀 Bot thread started")
        main()

    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    print("✅ Bot thread launched")

    app.run(host='0.0.0.0', port=8080)