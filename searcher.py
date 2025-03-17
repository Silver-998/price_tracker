import requests
import time
from datetime import datetime

# Function to get all available symbols from Binance
def get_available_symbols():
    # For spot trading pairs
    spot_url = "https://api.binance.com/api/v3/exchangeInfo"
    # For futures trading pairs
    futures_url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    
    spot_symbols = []
    futures_symbols = []
    
    try:
        # Get spot trading pairs
        spot_response = requests.get(spot_url)
        spot_data = spot_response.json()
        spot_symbols = [symbol['symbol'] for symbol in spot_data['symbols']]
        print(f"Found {len(spot_symbols)} spot trading pairs")
        
        # Get futures trading pairs
        futures_response = requests.get(futures_url)
        futures_data = futures_response.json()
        futures_symbols = [symbol['symbol'] for symbol in futures_data['symbols']]
        print(f"Found {len(futures_symbols)} futures trading pairs")
        
        return {
            "spot": spot_symbols,
            "futures": futures_symbols
        }
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return {"spot": [], "futures": []}

# Function to find closest match to user's input
def find_closest_match(user_input, available_symbols):
    # Convert to uppercase for consistency
    user_input = user_input.upper()
    
    # Exact match
    if user_input in available_symbols["spot"]:
        return ("spot", user_input)
    if user_input in available_symbols["futures"]:
        return ("futures", user_input)
    
    # Partial match (symbol contains the user input)
    spot_matches = [s for s in available_symbols["spot"] if user_input in s]
    futures_matches = [s for s in available_symbols["futures"] if user_input in s]
    
    # Return first match if any found
    if spot_matches:
        return ("spot", spot_matches[0])
    if futures_matches:
        return ("futures", futures_matches[0])
    
    # No match found
    return (None, None)

# Function to fetch price for a symbol
def fetch_price(market_type, symbol, interval_seconds):
    if market_type == "spot":
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    elif market_type == "futures":
        url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
    else:
        print("Invalid market type")
        return
    
    print(f"Starting price fetch for {symbol} ({market_type}) every {interval_seconds} seconds...")
    
    try:
        while True:
            try:
                response = requests.get(url)
                data = response.json()
                
                # Format the timestamp
                now = datetime.now()
                timestamp = now.strftime("%H:%M:%S")
                
                # Format the price
                price_float = float(data['price'])
                formatted_price = f"${price_float:,.8f}" if price_float < 0.1 else f"${price_float:,.2f}"
                
                print(f"[{timestamp}] {data['symbol']}: {formatted_price}")
                
            except Exception as e:
                print(f"Error fetching price: {e}")
                print(f"Response: {response.text if 'response' in locals() else 'No response'}")
            
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\nPrice fetching stopped")

# Main function
def main():
    # Get available symbols first
    print("Fetching available trading pairs from Binance...")
    available_symbols = get_available_symbols()
    
    # Ask user for input
    user_symbol = input("Enter the cryptocurrency symbol to track (e.g., BTCUSDT, ETHUSDT): ")
    
    # Find matching symbol
    market_type, matched_symbol = find_closest_match(user_symbol, available_symbols)
    
    if matched_symbol:
        print(f"Found matching symbol: {matched_symbol} on {market_type} market")
        interval = int(input("Enter update interval in seconds (default: 30): ") or "30")
        fetch_price(market_type, matched_symbol, interval)
    else:
        print(f"No matching symbol found for '{user_symbol}'")
        print("Available options containing similar names:")
        
        # Show some suggestions
        user_base = ''.join([c for c in user_symbol.upper() if c.isalpha()])
        if len(user_base) >= 3:
            spot_suggestions = [s for s in available_symbols["spot"] if user_base in s][:5]
            futures_suggestions = [s for s in available_symbols["futures"] if user_base in s][:5]
            
            if spot_suggestions:
                print("Spot market suggestions:")
                for s in spot_suggestions:
                    print(f"  - {s}")
            
            if futures_suggestions:
                print("Futures market suggestions:")
                for s in futures_suggestions:
                    print(f"  - {s}")

if __name__ == "__main__":
    main()