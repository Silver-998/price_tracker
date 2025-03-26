import websocket
import json
import threading
import time
from datetime import datetime
import ssl
import RPi.GPIO as GPIO
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from PIL import Image, ImageDraw, ImageFont

# GPIO Button Setup
PIN_L1 = 17  # GPIO pin for L1
PIN_L2 = 27  # GPIO pin for L2
PIN_R1 = 22  # GPIO pin for R1
PIN_R2 = 23  # GPIO pin for R2

# Configure GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_L1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_L2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_R1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_R2, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Available trading pairs - add more as needed
TRADING_PAIRS = [
    'fartcoinusdt',
    'pnutusdt',
    'melaniausdt',
    'popcatusdt'     
]

# OLED Display Setup
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=32)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)

# Configuration
current_pair_index = 0
symbol = TRADING_PAIRS[current_pair_index]  # Start with fartcoinusdt
binance_ws_url = f"wss://fstream.binance.com/ws/{symbol}@ticker"

# Use thread lock for thread-safe access to shared variables
lock = threading.Lock()
display_text = "Connecting"
display_symbol = symbol.upper().replace('USDT', '/USDT')
last_update_time = time.time()
running = True
ws_app = None

def update_display():
    """Update the OLED display with current price info"""
    global display_text, display_symbol
    try:
        # Thread-safe access to display_text
        with lock:
            current_text = display_text
            current_symbol = display_symbol
        
        # Create blank image (128x32)
        image = Image.new("1", (128, 32), "black")
        draw = ImageDraw.Draw(image)
        
        # Draw boundary box
        draw.rectangle((0, 0, 127, 31), outline="white", fill="black")
        
        # Draw symbol at top
        small_font = ImageFont.load_default()
        draw.text((3, 1), current_symbol, font=small_font, fill="white")
        
        # Draw price below
        font = ImageFont.load_default()
        draw.text((3, 14), str(current_text), font=font, fill="white")
       
        # Display image
        device.display(image)
        print(f"Display updated: {current_symbol} - {current_text}")
    except Exception as e:
        print(f"Display error: {e}")

def display_loop():
    """Thread function to update the display regularly"""
    global running
    while running:
        update_display()
        time.sleep(1)  # Update display every second

def connection_watchdog():
    """Thread function to monitor connection and restart if needed"""
    global running, last_update_time, ws_app
    
    while running:
        current_time = time.time()
        with lock:
            time_since_update = current_time - last_update_time
            
        # If no price updates for over 30 seconds, show error and reconnect
        if time_since_update > 30:
            print("Watchdog: Connection seems dead, reconnecting...")
            with lock:
                display_text = "Reconnecting..."
            
            # Force WebSocket to reconnect
            try:
                ws_app.close()
            except:
                pass
            
            # WebSocket will auto-reconnect due to enable_reconnect=True
            
        time.sleep(10)  # Check every 10 seconds

def on_message(ws, message):
    """Callback when WebSocket receives a message"""
    global display_text, last_update_time
    
    try:
        data = json.loads(message)
        
        # Extract the price from the ticker data
        price_float = float(data['c'])  # 'c' is the current price in ticker stream
        price_fm = f"${price_float:,.4f}"        
        # Thread-safe update of shared variable
        with lock:
            display_text = str(price_fm)
            last_update_time = time.time()
            
        print(f"New price: {price_fm}")
        
    except Exception as e:
        print(f"Error processing message: {e}")

def on_error(ws, error):
    """Callback when WebSocket encounters an error"""
    print(f"WebSocket error: {error}")
    with lock:
        display_text = "Error: WS"

def on_close(ws, close_status_code, close_msg):
    """Callback when WebSocket connection closes"""
    print(f"WebSocket closed: {close_status_code} - {close_msg}")
    with lock:
        display_text = "Disconnected"

def on_open(ws):
    """Callback when WebSocket connection opens"""
    print("WebSocket connection established")
    with lock:
        display_text = "Connected"

def change_symbol(new_index):
    """Change to a new trading pair"""
    global symbol, binance_ws_url, ws_app, display_symbol
    
    # Set new symbol
    symbol = TRADING_PAIRS[new_index]
    binance_ws_url = f"wss://fstream.binance.com/ws/{symbol}@ticker"
    
    with lock:
        display_text = "Switching..."
        display_symbol = symbol.upper().replace('USDT', '/USDT')
    
    print(f"Switching to {symbol}")
    
    # Close existing connection
    if ws_app:
        ws_app.close()
    
    # WebSocket will be recreated in main loop

def check_buttons():
    """Thread function to check button states"""
    global current_pair_index, running
    
    # Debounce time in seconds
    debounce_time = 0.3
    last_button_time = time.time() - debounce_time
    
    while running:
        current_time = time.time()
        
        # Only check buttons if enough time has passed since last press
        if current_time - last_button_time >= debounce_time:
            # Check button S1 (L1 + R1)
            if GPIO.input(PIN_L1) == GPIO.LOW and GPIO.input(PIN_R1) == GPIO.LOW:
                print("Button S1 pressed")
                current_pair_index = 0  # First trading pair
                change_symbol(current_pair_index)
                last_button_time = current_time
            
            # Check button S2 (L2 + R1)
            elif GPIO.input(PIN_L2) == GPIO.LOW and GPIO.input(PIN_R1) == GPIO.LOW:
                print("Button S2 pressed")
                current_pair_index = 1  # Second trading pair
                change_symbol(current_pair_index)
                last_button_time = current_time
            
            # Check button S3 (L1 + R2)
            elif GPIO.input(PIN_L1) == GPIO.LOW and GPIO.input(PIN_R2) == GPIO.LOW:
                print("Button S3 pressed")
                current_pair_index = 2  # Third trading pair
                change_symbol(current_pair_index)
                last_button_time = current_time
            
            # Check button S4 (L2 + R2)
            elif GPIO.input(PIN_L2) == GPIO.LOW and GPIO.input(PIN_R2) == GPIO.LOW:
                print("Button S4 pressed")
                current_pair_index = 3  # Fourth trading pair
                change_symbol(current_pair_index)
                last_button_time = current_time
        
        time.sleep(0.1)  # Check buttons every 100ms

def start_websocket():
    """Start the WebSocket connection"""
    global ws_app, binance_ws_url
    
    # WebSocket setup with auto reconnect
    websocket.enableTrace(False)  # Set to True for detailed WebSocket logs
    ws_app = websocket.WebSocketApp(
        binance_ws_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    
    # Start the WebSocket connection in a separate thread
    ws_thread = threading.Thread(
        target=lambda: ws_app.run_forever(
            sslopt={"cert_reqs": ssl.CERT_NONE},
            ping_interval=30,
            ping_timeout=10,
            reconnect=5  # Reconnect automatically with a 5-second delay
        )
    )
    ws_thread.daemon = True
    ws_thread.start()

def main():
    global running, ws_app, last_update_time
    
    try:
        # Start display thread
        display_thread = threading.Thread(target=display_loop)
        display_thread.daemon = True
        display_thread.start()
        
        # Start watchdog thread
        watchdog_thread = threading.Thread(target=connection_watchdog)
        watchdog_thread.daemon = True
        watchdog_thread.start()
        
        # Start button checking thread
        button_thread = threading.Thread(target=check_buttons)
        button_thread.daemon = True
        button_thread.start()
        
        # Initialize last_update_time
        with lock:
            last_update_time = time.time()
        
        # Start WebSocket
        start_websocket()
        
        # Main thread just keeps the program running
        while running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        running = False
        if ws_app:
            ws_app.close()
        GPIO.cleanup()  # Clean up GPIO on exit
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    finally:
        GPIO.cleanup()  # Ensure GPIO cleanup happens even on error