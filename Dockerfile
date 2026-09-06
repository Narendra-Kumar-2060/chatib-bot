FROM python:3.10-slim

# Install Firefox and dependencies
RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Geckodriver
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-linux64.tar.gz" \
    && tar -xzf geckodriver-v0.35.0-linux64.tar.gz \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin/

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your bot script
COPY chatib_bot.py .

# Run the bot
CMD ["python", "chatib_bot.py"]