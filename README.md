# MetaTrader5 Telegram Trading Bot

Telegram bot that receives GOLD (XAUUSD) trade alerts and places two pending orders on MetaTrader5 — one at each entry price — with the specified TP and SL. Includes an optional forwarder that automatically relays alerts from a signal channel to your bot.

---

## Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

You should see `(.venv)` at the start of your terminal prompt. Always activate the venv before running anything.

> To deactivate when you're done: `deactivate`

---

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

> Requires Python 3.10+ and a 64-bit Windows machine with MetaTrader5 terminal installed.

---

### 3. Create your `.env` file

```powershell
copy .env.example .env
```

Open `.env` and fill in your values:

```
TELEGRAM_TOKEN=your_bot_token_here
ALLOWED_CHAT_ID=your_chat_id_here
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server

# Only needed if using forwarder.py
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
SOURCE_CHANNEL=@signal_channel_username
TARGET_GROUP=-1001234567890
```

---

### 4. Get your Telegram bot token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token (looks like `123456789:ABCdef...`) into `TELEGRAM_TOKEN`

---

### 5. Get your chat ID

**Option A — Private chat with the bot:**
1. Add your bot on Telegram and send any message
2. Run `main.py` and check the terminal — it logs every incoming chat ID

**Option B — A group:**
1. Add your bot to the group
2. Send `/chatid` — the bot logs the group's ID to the terminal (negative number like `-1001234567890`)

Put that number into `ALLOWED_CHAT_ID`.

---

### 6. Enable Algo Trading in MetaTrader5

1. Open MetaTrader5
2. Go to **Tools → Options → Expert Advisors**
3. Check **Allow automated trading**
4. Click OK
5. Make sure the **AutoTrading** button in the toolbar is active (green)

---

### 7. Run the bot

```powershell
python main.py
```

The bot will connect to MT5 on startup and log the result. Keep the terminal open while trading.

---

## Forwarder (optional)

`forwarder.py` watches a Telegram channel you don't own and automatically forwards GOLD alerts to your group, where the trading bot picks them up.

### Setup

1. Get your Telegram API credentials:
   - Go to [my.telegram.org](https://my.telegram.org) → log in
   - Click **API Development Tools** → create an app
   - Copy `api_id` and `api_hash` into `.env`

2. Fill in the forwarder variables in `.env`:
   ```
   TELEGRAM_API_ID=12345678
   TELEGRAM_API_HASH=abc123...
   SOURCE_CHANNEL=@thesignalchannel
   TARGET_GROUP=-1001234567890
   ```

3. Run in a second terminal (with venv activated):
   ```powershell
   python forwarder.py
   ```
   The first run will ask for your phone number and a Telegram verification code. After that it saves a session file and logs in automatically.

### How it works

```
Signal channel → forwarder.py → your group → main.py → MT5 orders
```

Only messages containing `GOLD BUY` or `GOLD SELL` are forwarded. Everything else is ignored.

---

## Alert Message Format

```
♾ 🥇 GOLD SELL 4676 - 4781

➡️TP : 4669
➡️TP : 4656
➡️TP : 4500
➡️TP : OPEN
⛔️SL : 4696
```

| Part | Meaning |
|---|---|
| `GOLD BUY / SELL` | Direction |
| `4676 - 4781` | Two entry prices — one pending order placed at each |
| `TP : 4669` | Only the **first** numeric TP is used |
| `TP : OPEN` | Ignored |
| `SL : 4696` | Stop Loss for both orders |

The bot places two pending orders and replies with each ticket number or error.

---

## Commands

| Command | Description |
|---|---|
| `/status` | MT5 connection status, account balance & equity |
| `/open` | Current open positions and pending orders with live price, TP/SL distances and profit |
| `/trades` | Last 5 trades logged to `trades.csv` |
| `/help` | Alert format and command list |

The terminal also logs the chat ID and name of every incoming message — useful for finding group or channel IDs.

---

## Trade Log

Every order attempt is saved to `trades.csv`:

```
timestamp, action, symbol, entry_price, tp, sl, lot, status, ticket, error
```

Each alert generates two rows — one per entry price.
