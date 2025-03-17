from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json

url = 'https://pro-api.coinmarketcap.com/v4/dex/pairs/quotes/latest'
parameters = {
  'symbol': 'FARTCOIN',  # Replace with your desired cryptocurrency symbol
  'convert': 'USD'  # The currency you want the price in
  
headers = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': 'cc9bcba4-b84c-4f21-8e66-6ec9124e5891',
}

session = Session()
session.headers.update(headers)

try:
  response = session.get(url, params=parameters)
  data = json.loads(response.text)
  print(data)
except (ConnectionError, Timeout, TooManyRedirects) as e:
  print(e)