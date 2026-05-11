Build me a complete MetaTrader5 Telegram trading bot. Here are all the requirements:

## Project Structure
Create these files: main.py, trader.py, config.py, .env.example, requirements.txt, README.md

## Requirements
- python-telegram-bot
- MetaTrader5
- python-dotenv

## Config (config.py)
- LOT_SIZE = 0.01 (fixed, never changes)
- MAGIC_NUMBER = 123456

## .env.example
TELEGRAM_TOKEN=your_bot_token_here
ALLOWED_CHAT_ID=your_chat_id_here
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server

## trader.py — MT5 Logic
- connect() function that initializes MT5 with login/password/server from .env
- disconnect() function
- place_order(action, symbol, tp, sl) function with fixed 0.01 lot
- get_status() function that returns connection status and account balance/equity
- All functions must log activity and return human-readable result strings

## main.py — Telegram Bot
- On startup, automatically connect to MT5
- ALLOWED_CHAT_ID security check on every message — silently ignore unauthorized chats
- Handle trade alerts in this format: BUY EURUSD TP:1.1050 SL:1.0980
- /status command — shows MT5 connection status, account balance, equity
- /help command — shows the alert format and available commands
- /trades command — shows last 5 executed trades from the log
- Reply to every alert with success or error message
- If MT5 disconnects, attempt auto-reconnect before placing order

## Trade Logging
- Log every trade attempt to trades.csv with columns:
  timestamp, action, symbol, tp, sl, lot, status, ticket, error
- /trades command reads and displays the last 5 rows from this CSV

## Error Handling
- Handle: symbol not found, MT5 not connected, invalid message format,
  requote errors, off-quotes, not enough money, invalid stops
- On any MT5 error, retry once then report failure to Telegram

## README.md
Write a clear setup guide covering:
1. Install Python dependencies
2. Create .env from .env.example and fill in values
3. How to get Telegram bot token from BotFather
4. How to get chat ID from userinfobot
5. How to enable Algo Trading in MT5
6. How to run the bot
7. Alert message format examples