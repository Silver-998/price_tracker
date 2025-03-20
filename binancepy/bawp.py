import websocket
import json
import threading
import time
from datetime import datetime
import ssl
from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from PIL import Image, ImageDraw, ImageFont

# OLED Display Setup
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=32)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)

# Configuration
symbol = 'fartcoinusdt'  # Lowercase for Binance WebSocket
binance_ws_url = f"wss://fstream.binance.com/ws/{symbol}@ticker"

# Use thread lock for thread-safe access to shared variables
lock = threading.Lock()
display_text = "Connecting..."
last_update_time = time.time()
running = True

def update_display():
    """Update the OLED display with current price info"""
    global display_text
    try:
        # Thread-safe access to display_text
        with lock:
            current_text = display_text
            current_time = time.strftime("%H:%M:%S")
        
        # Create blank image (128x32)
        image = Image.new("1", (128, 32), "black")
        draw = ImageDraw.Draw(image)
        
        # Draw boundary box
        draw.rectangle((0, 0, 127, 31), outline="white", fill="black")
        
        # Draw price
        font = ImageFont.load_default(size=24)
        draw.text((3, 3), str(current_text), font=font, fill="white")
       
        
        # Display image
        device.display(image)
        print(f"Display updated: {current_text} at {current_time}")
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

def main():
    global running, ws_app
    
    # Start display thread
    display_thread = threading.Thread(target=display_loop)
    display_thread.daemon = True
    display_thread.start()
    
    # Start watchdog thread
    watchdog_thread = threading.Thread(target=connection_watchdog)
    watchdog_thread.daemon = True
    watchdog_thread.start()
    
    # Initialize last_update_time
    with lock:
        last_update_time = time.time()
    
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
    
    try:
        # Main thread just keeps the program running
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        running = False
        ws_app.close()
        time.sleep(1)

if __name__ == "__main__":
    main()