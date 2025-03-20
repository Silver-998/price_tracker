from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from PIL import Image, ImageDraw, ImageFont
import json
import threading
import time

# Initialize OLED for 128x32 resolution
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=32)

font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)

url = 'https://pro-api.coinmarketcap.com/v4/dex/pairs/quotes/latest'

parameters = {
  'symbol': 'FARTCOIN',  # Replace with your desired cryptocurrency symbol
  'convert': 'USD'  # The currency you want the price in
}

headers = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': 'cc9bcba4-b84c-4f21-8e66-6ec9124e5891',
}

session = Session()
session.headers.update(headers)

running = True
display_text = "Initializing.._"

def update_ds()
    # Create blank image (128x32)
    image = Image.new("1", (128, 32), "black")
    draw = ImageDraw.Draw(image)
    
    # Debug: Draw full boundary box
    draw.rectangle((0, 0, 127, 31), outline="white", fill="black")
    
    # Adjust text position to be clearly visible
    draw.text((1, 1), display_text, font=font, fill="white")
    
    # Display image
    device.display(image)
    print(f"Display updated with: {display_text}")
    
def input_loop():
    """Function that handles user input"""
    global running   
    while running:
        user_input = input()
        if user_input.strip().lower() == "quit":
            print("Shutting down...")
            running = False
            break        

def display_loop():
    global running
    while running:
        update_display()
        time.sleep(30)

def check_price():
    global running
    if not running:
        return  # Exit if we're no longer running
    try:
        response = session.get(url, params=parameters)
        #raw_json = response.text
        #print(raw_json)
        data = json.loads(response.text)
        fart_p = data['data']['FARTCOIN'][0]['quote']['USD']['price']
        fart_pr = round(fart_p,5)
        print(fart_pr)      
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)
    if running:
        timer = threading.Timer(60.0, check_price)
        timer.daemon = True  # This ensures the timer won't prevent program exit
        timer.start()

            
if __name__ == "__main__":    
    # Start the price checking immediately and then every 30 seconds
    check_price()
    
    # Start the input handling loop
    input_loop()
    
    print("Program terminated.")