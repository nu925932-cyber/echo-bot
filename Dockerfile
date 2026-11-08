FROM python:3.11-slim  
WORKDIR /app  
COPY . .  
RUN pip install --no-cache-dir requests flask python-telegram-bot  
CMD ["python", "bot.py"] 
