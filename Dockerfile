FROM mcr.microsoft.com/playwright/python:v1.46.0

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your bot script
COPY chatib_bot.py .

# Run the bot
CMD ["python", "chatib_bot.py"]