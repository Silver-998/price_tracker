import requests
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from PIL import Image, ImageDraw, ImageFont
import json
import threading
import time
from datetime import datetime

# Configuration
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=32)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
symbol = 'FARTCOINUSDT'  # Change to your desired currency pair
interval_seconds = 5
binance_url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
running = True

lock = threading.Lock()
display_text = "Initializing..."
last_update_time = time.time()

def update_ds():
    global display_text
    try:
        # Thread-safe access to display_text
        with lock:
            current_text = display_text
            current_time = time.strftime("%H:%M:%S")
        # Create blank image (128x32)
        image = Image.new("1", (128, 32), "black")
        draw = ImageDraw.Draw(image)
        # Debug: Draw full boundary box
        draw.rectangle((0, 0, 127, 31), outline="white", fill="black")
        # Adjust text position to be clearly visible
        font = ImageFont.load_default(size=24) # Increase size from whatever default was
        draw.text((1, 1), str(display_text), font=font, fill="white")
        # Display image
        device.display(image)
        print(f"Display updated with: {display_text}")
    except Exception as e:
        print(f"Display error: {e}")  

def display_loop():
    global running
    while running:
        update_ds()
        time.sleep(2)
   

def fetch_price():
    global display_text, last_update_time
    try:
        response = requests.get(binance_url)
        data = response.json()
        
        # Format the price with commas for 1/1.000
        price_float = float(data['price'])
        price_fm = f"${price_float:,.4f}"
        display_text = str(price_fm)
        print(price_fm)
        
    except Exception as e:
        print(f"Error fetching price: {e}")

def connection_watchdog():
    """Monitor connection and restart if needed"""
    global running, last_update_time
    
    while running:
        current_time = time.time()
        with lock:
            time_since_update = current_time - last_update_time
            
        # If no price updates for over 2 minutes, force a refresh
        if time_since_update > 120:
            print("Watchdog: No updates for 2 minutes, forcing refresh...")
            fetch_price()
            
        time.sleep(30)  # Check every 30 seconds


def main():
    global running
    display_thread = threading.Thread(target=display_loop)
    display_thread.daemon = True
    display_thread.start()
    try:
        while running:
            fetch_price()
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nShutting down...")
        running = False
        time.sleep(1)

if __name__ == "__main__":
    main()