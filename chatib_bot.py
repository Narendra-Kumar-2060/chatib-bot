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
WAIT_TIMEOUT = 30
ADMIN_USERNAME = "UnfriendLy"

# ---------- Proxy List (optional) ----------
PROXIES = [
    # Add your proxies here, e.g.:
    # "http://user:pass@proxy1:8080",
    # "http://proxy2:8080",
]

def generate_letter_string(length=6):
    return "".join(random.choices(string.ascii_letters, k=length))

def send_message(page, text):
    try:
        page.fill("#contenteditablediv", text)
        page.click(".msg_send_btn")
        time.sleep(0.2)                     # Faster
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

    send_message(page, "I'm thinking of a number between 1 and 100.")

    # Track how many chat messages we've already scanned, so each message is
    # processed exactly once — regardless of whether its text repeats
    # something sent earlier. This replaces content-based dedup, which
    # wrongly ignored a command/guess if the exact same text was ever sent
    # before.
    processed_count = 0
    poll_interval = 1
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
            processed_count = 0  # DOM reset — start scanning from scratch
            last_activity = time.time()
            continue

        try:
            elements = page.query_selector_all(".received_withd_msg")

            # If the message list ever shrinks (e.g. unexpected DOM reset),
            # our old count is stale — rescan from the top rather than
            # silently skipping messages or crashing on a bad slice.
            if processed_count > len(elements):
                processed_count = 0

            new_elements = elements[processed_count:]
            acted_this_poll = False  # only act on ONE game command per poll
            stop_index = len(new_elements)  # how far into new_elements we got

            for idx, elem in enumerate(new_elements):
                raw = elem.inner_text().strip()
                if not raw:
                    continue

                user, msg = parse_message(raw)
                # Skip anything we couldn't attribute to a user, and skip
                # the bot's own messages.
                if user is None or user == bot_username:
                    continue

                lower_msg = msg.lower().strip()

                # ---------------- ADMIN COMMANDS ----------------
                # Not subject to the one-per-poll limit or pause state.
                # Only intercepts KNOWN admin commands — anything else
                # (like the admin's own !guess) falls through to normal
                # game logic below instead of being silently swallowed.
                if user == ADMIN_USERNAME and lower_msg in ADMIN_COMMANDS:
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
                    continue

                if paused:
                    continue

                if not lower_msg.startswith("!guess"):
                    continue

                if acted_this_poll:
                    # A guess already got a response this poll — stop here
                    # and pick this message up on the *next* poll instead of
                    # evaluating it against a target that may have just
                    # changed underneath us.
                    stop_index = idx
                    break

                parts = msg.split()
                if len(parts) != 2:
                    send_message(page, f"{user}, use: !guess [number]")
                    acted_this_poll = True
                    continue

                try:
                    guess = int(parts[1])
                except ValueError:
                    send_message(page, f"{user}, please provide a valid number.")
                    acted_this_poll = True
                    continue

                if guess == target:
                    reply = f"Correct, {user}! The number was {target}. New round!"
                    send_message(page, reply)
                    # ---- NEW ROUND ----
                    target = random.randint(1, 100)
                    round_number += 1
                    print(f"🎯 (DEBUG) New target: {target} (Round {round_number})")
                    send_message(page, f"I'm thinking of a new number between 1 and 100. (Round {round_number})")
                elif guess < target:
                    send_message(page, f"Too low, {user}!")
                else:
                    send_message(page, f"Too high, {user}!")

                acted_this_poll = True

            # Mark as processed everything up through stop_index. If we
            # deferred a guess (stop_index < len(new_elements)), that one
            # and anything after it will be picked up again next poll.
            processed_count += stop_index

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

                page.goto(SITE_URL)
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