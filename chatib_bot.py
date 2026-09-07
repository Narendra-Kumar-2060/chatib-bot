from playwright.sync_api import sync_playwright
from flask import Flask
import threading
import time
import random
import string

app = Flask(__name__)

# ---------- Configuration ----------
SITE_URL = "https://www.chatib.us"
ROOM_URL = "https://www.chatibrooms.com/user/chatroom/sports-chat-room"
TOKEN_URL = "https://www.chatib.us/auth/generateSsoToken/sports-chat-room"
WAIT_TIMEOUT = 60   # from 30
ADMIN_USERNAME = "UnfriendLy"

# ---------- Proxy List (optional) ----------
PROXIES = [
    # Add your proxies here, e.g.:
    # "http://user:pass@proxy1:8080",
    # "http://proxy2:8080",
]

def generate_letter_string(length=6):
    return "".join(random.choices(string.ascii_letters, k=length))

def wait_and_fill(page, selector, text, timeout=WAIT_TIMEOUT):
    """Wait for element, clear and fill it."""
    try:
        page.wait_for_selector(selector, timeout=timeout * 1000)
        page.fill(selector, text)
        return True
    except Exception as e:
        print(f"⚠️ Failed to fill {selector}: {e}")
        return False

def wait_and_click(page, selector, timeout=WAIT_TIMEOUT):
    """Wait for element and click it."""
    try:
        page.wait_for_selector(selector, timeout=timeout * 1000)
        page.click(selector)
        return True
    except Exception as e:
        print(f"⚠️ Failed to click {selector}: {e}")
        return False

def wait_and_select(page, selector, value, timeout=WAIT_TIMEOUT):
    """Wait for a <select> element and select an option by visible text."""
    try:
        page.wait_for_selector(selector, timeout=timeout * 1000)
        page.select_option(selector, value)
        return True
    except Exception as e:
        print(f"⚠️ Failed to select {selector}: {e}")
        return False

def send_message(page, text):
    try:
        page.wait_for_selector("#contenteditablediv", timeout=5000)
        page.fill("#contenteditablediv", text)
        page.click(".msg_send_btn")
        time.sleep(0.2)
        return True
    except Exception as e:
        print(f"⚠️ Failed to send message: {e}")
        return False

def login(page):
    print("\n--- Logging in ---")
    random_username = generate_letter_string(6)
    random_number = random.randint(1000, 9999)
    full_username = f"LemonTree{random_number}"

    if not wait_and_fill(page, "#username", full_username):
        raise Exception("Username field not found or fill failed")
    print("✅ Username entered")

    if not wait_and_click(page, ".checkmark-male"):
        raise Exception("Gender field not clickable")
    print("✅ Gender selected")

    # --- Age dropdown ---
    if not wait_and_select(page, "#age", "24"):
        raise Exception("Age dropdown selection failed")
    print("✅ Age selected")

    # --- Country dropdown ---
    if not wait_and_select(page, "#login_country", "United States"):
        raise Exception("Country dropdown selection failed")
    print("✅ Country selected")

    time.sleep(2)  # give city list time to populate

    # --- City dropdown ---
    try:
        if not wait_and_select(page, "#city", "New York"):
            print("⚠️ City not found, using first available")
            page.wait_for_selector("#city", timeout=5000)
            page.select_option("#city", index=1)
    except:
        pass
    print("✅ City selected")

    if not wait_and_click(page, "#startChatNow"):
        raise Exception("Start button not found")
    print("✅ Start button clicked")

    time.sleep(2)
    try:
        wait_and_click(page, ".btn.btn-primary.confirm_decline.agree", timeout=5)
        print("✅ TOS popup accepted")
    except:
        print("⚠️ TOS popup not found – continuing.")

    print("✅ Login complete.")
    return full_username

def navigate_to_room(page):
    print("\n--- Navigating to room ---")
    # Retry token endpoint up to 3 times
    for attempt in range(3):
        try:
            page.goto(TOKEN_URL, timeout=WAIT_TIMEOUT * 1000)
            break
        except Exception as e:
            print(f"⚠️ Token attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise
            time.sleep(2)
    print("✅ Token endpoint visited")
    time.sleep(2)

    if "chatibrooms" not in page.url:
        for attempt in range(3):
            try:
                page.goto(ROOM_URL, timeout=WAIT_TIMEOUT * 1000)
                break
            except Exception as e:
                print(f"⚠️ Room URL attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    raise
                time.sleep(2)
        print("✅ Room URL loaded")
    else:
        print("✅ Already on room page.")

    try:
        page.wait_for_selector(".received_withd_msg", timeout=WAIT_TIMEOUT * 1000)
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
        if not user:
            return None, None
        return user, msg
    # Couldn't identify a username line — do NOT return raw text with a None
    # user, since that bypasses the bot's own-message filter downstream.
    return None, None

    
def monitor_and_play(page, bot_username):
    print("\n--- Game monitor started ---")
    target = random.randint(1, 100)
    round_number = 0
    print(f"🎯 (DEBUG) Target: {target} (Round {round_number})")

    # --- Wait for chat input to be ready ---
    try:
        page.wait_for_selector("#contenteditablediv", timeout=5000)
        time.sleep(0.5)
    except Exception as e:
        print(f"⚠️ Chat input not found: {e}")
        return  # exit monitor, will restart session

    send_message(page, "I'm thinking of a number between 1 and 100.")
    
    # --- Track last processed messages ---
    last_processed = None          # (user, msg, round) for game guesses
    last_admin_raw = None          # raw text of last processed admin command

    poll_interval = 0.3
    last_activity = time.time()
    paused = False
    ADMIN_COMMANDS = {"!pause", "!resume", "!status", "!newtarget", "!stop"}

    while True:
        if "chatibrooms" not in page.url:
            print("⚠️ Redirected away from room page – possible IP ban.")
            break

        if time.time() - last_activity > 60:
            print("⚠️ No activity for 60 seconds. Refreshing page...")
            page.reload()
            page.wait_for_load_state("networkidle")   # wait for page to settle
            last_processed = None
            last_admin_raw = None
            last_activity = time.time()
            continue

        try:
            elements = page.query_selector_all(".received_withd_msg")
            if not elements:
                time.sleep(poll_interval)
                continue

            newest = elements[-1]
            raw = newest.inner_text().strip()
            if not raw:
                time.sleep(poll_interval)
                continue

            user, msg = parse_message(raw)
            if user is None or user == bot_username:
                time.sleep(poll_interval)
                continue

            lower_msg = msg.lower().strip()

            # ---------------- ADMIN COMMANDS ----------------
            # Admin commands are tracked by raw text (to avoid reprocessing the same message)
            if user == ADMIN_USERNAME and lower_msg in ADMIN_COMMANDS:
                # Skip if this exact raw message was already processed
                if raw == last_admin_raw:
                    time.sleep(poll_interval)
                    continue
                last_admin_raw = raw

                if lower_msg == "!pause":
                    paused = True
                    send_message(page, "⏸️ Game paused by admin.")
                elif lower_msg == "!resume":
                    paused = False
                    send_message(page, "▶️ Game resumed by admin.")
                elif lower_msg == "!status":
                    state = "paused" if paused else "running"
                    send_message(
                        page,
                        f"ℹ️ Status: {state} | Round {round_number} | Target={target}",
                    )
                elif lower_msg == "!newtarget":
                    target = random.randint(1, 100)
                    round_number += 1
                    print(f"🎯 (DEBUG) Admin reset target: {target} (Round {round_number})")
                    send_message(page, f"🎲 Admin reset the number. (Round {round_number})")
                elif lower_msg == "!stop":
                    send_message(page, "🛑 Bot stopping (admin command).")
                    print("🛑 Stopped via admin command.")
                    return "stop"
                time.sleep(poll_interval)
                continue

            # If paused, ignore everything else
            if paused:
                time.sleep(poll_interval)
                continue

            if not lower_msg.startswith("!guess"):
                time.sleep(poll_interval)
                continue

            # ---- Game guess: track with (user, msg, round) ----
            current_key = (user, msg, round_number)
            if current_key == last_processed:
                # Same guess already processed in this round – skip
                time.sleep(poll_interval)
                continue
            last_processed = current_key

            parts = msg.split()
            if len(parts) != 2:
                send_message(page, f"{user}, use: !guess [number]")
                time.sleep(poll_interval)
                continue

            try:
                guess = int(parts[1])
            except ValueError:
                send_message(page, f"{user}, please provide a valid number.")
                time.sleep(poll_interval)
                continue

            if guess == target:
                reply = f"Correct, {user}! The number was {target}. New round!"
                send_message(page, reply)
                target = random.randint(1, 100)
                round_number += 1
                print(f"🎯 (DEBUG) New target: {target} (Round {round_number})")
                send_message(page, f"I'm thinking of a new number between 1 and 100. (Round {round_number})")
            elif guess < target:
                send_message(page, f"Too low, {user}!")
            else:
                send_message(page, f"Too high, {user}!")

            time.sleep(poll_interval)
            last_activity = time.time()

        except Exception as e:
            print(f"⚠️ Error in monitor loop: {e}")
            time.sleep(poll_interval)
            
def main():
    proxy_index = 0
    retry_count = 0
    max_retries = 5

    while True:
        try:
            # Proxy support
            browser_args = ["--no-sandbox", "--disable-dev-shm-usage"]
            if PROXIES:
                proxy = PROXIES[proxy_index % len(PROXIES)]
                browser_args.append(f"--proxy-server={proxy}")
                print(f"🔄 Using proxy: {proxy}")

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=browser_args
                )
                page = browser.new_page()
                print("✅ Browser launched")


                for attempt in range(3):
                    try:
                        page.goto(SITE_URL, timeout=WAIT_TIMEOUT * 1000)
                        break
                    except Exception as e:
                        print(f"⚠️ Site load attempt {attempt+1} failed: {e}")
                        if attempt == 2:
                            raise
                        time.sleep(2)
                print("📄 Main page loaded")

                username = login(page)
                final_url = navigate_to_room(page)

                result = None
                if "chatibrooms" in final_url:
                    retry_count = 0
                    result = monitor_and_play(page, username)
                else:
                    print(f"⚠️ Not on room page – retrying...")
                    retry_count += 1

                browser.close()

                if result == "stop":
                    print("🛑 Admin stop received — bot thread exiting (Flask keeps serving).")
                    return

                print("🔄 Session ended, restarting...")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            retry_count += 1

        # Rotate proxy or wait if too many failures
        if retry_count >= max_retries:
            if PROXIES:
                proxy_index += 1
                print(f"🔄 Rotating to next proxy")
            else:
                print("⏳ Too many retries – waiting 5 minutes before retry...")
                time.sleep(300)      # 5 min cooldown
            retry_count = 0

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