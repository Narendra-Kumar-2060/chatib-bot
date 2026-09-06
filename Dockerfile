FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    wget curl gnupg unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install matching ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') \
    && CHROME_MAJOR=$(echo $CHROME_VERSION | cut -d'.' -f1) \
    && LATEST_RELEASE=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_$CHROME_MAJOR") \
    && wget -q "https://storage.googleapis.com/chrome-for-testing-public/$LATEST_RELEASE/linux64/chromedriver-linux64.zip" \
    && unzip chromedriver-linux64.zip \
    && chmod +x chromedriver-linux64/chromedriver \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/ \
    && rm -rf chromedriver-linux64.zip chromedriver-linux64

# **CRITICAL FIX: writable home directory**
RUN mkdir -p /home/daemon && chown daemon:daemon /home/daemon
ENV HOME=/home/daemon

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY chatib_bot.py .
CMD ["python", "chatib_bot.py"]