FROM mcr.microsoft.com/playwright/python:v1.46.0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

COPY chatib_bot.py .

CMD ["python", "chatib_bot.py"]