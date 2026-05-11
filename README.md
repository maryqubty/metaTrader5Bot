# MetaTrader5 Telegram Trading Bot

Telegram bot that receives GOLD (XAUUSD) trade alerts and places two pending orders on MetaTrader5 — one at each entry price — with the specified TP and SL.

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

> Requires Python 3.10+ and a 64-bit Windows machine with MetaTrader5 terminal installed.

---

### 2. Create your `.env` file

```bash
copy .env.example .env
```

Open `.env` and fill in your values:

```
TELEGRAM_TOKEN=your_bot_token_here
ALLOWED_CHAT_ID=your_chat_id_here
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server
```

---

### 3. Get your Telegram bot token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token (looks like `123456789:ABCdef...`) into `TELEGRAM_TOKEN`

---

### 4. Get your Telegram chat ID

1. Search for **@userinfobot** on Telegram
2. Send `/start` — it will reply with your numeric chat ID
3. Copy that number into `ALLOWED_CHAT_ID`

> Only messages from this chat ID will be processed. All others are silently ignored.

---

### 5. Enable Algo Trading in MetaTrader5

1. Open MetaTrader5
2. Go to **Tools → Options → Expert Advisors**
3. Check **Allow automated trading**
4. Click OK
5. Make sure the **AutoTrading** button in the toolbar is active (green)

---

### 6. Run the bot

```bash
python main.py
```

The bot will connect to MT5 on startup and log the result. Keep the terminal open while trading.

---

## Alert Message Format

Send alerts directly to your bot in this format:

```
GOLD SELL 4678 - 4793, TP: 4671, SL: 4698
GOLD BUY 2650 - 2660, TP: 2680, SL: 2635
```

| Part | Meaning |
|---|---|
| `GOLD` | Fixed symbol (always XAUUSD) |
| `BUY` / `SELL` | Trade direction |
| `4678 - 4793` | Two entry prices — one pending order placed at each |
| `TP: 4671` | Take Profit for both orders |
| `SL: 4698` | Stop Loss for both orders |

The bot will reply confirming each order ticket or reporting the error.

---

## Commands

| Command | Description |
|---|---|
| `/status` | MT5 connection status, account balance & equity |
| `/trades` | Last 5 trades logged to `trades.csv` |
| `/help` | Alert format reminder and command list |

---

## Trade Log

Every order attempt is saved to `trades.csv` with columns:

```
timestamp, action, symbol, entry_price, tp, sl, lot, status, ticket, error
```

Each alert generates two rows — one per entry price.
