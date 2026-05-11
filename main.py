import csv
import logging
import os
import re
from collections import deque
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import trader
from config import SYMBOL, TRADES_CSV

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ALLOWED_CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])

ALERT_RE = re.compile(
    r"^GOLD\s+(BUY|SELL)\s+([\d.]+)\s*-\s*([\d.]+),?\s*TP:\s*([\d.]+),?\s*SL:\s*([\d.]+)$",
    re.IGNORECASE,
)

HELP_TEXT = (
    "MetaTrader5 GOLD Trading Bot\n\n"
    "Alert format:\n"
    "  GOLD BUY 2650 - 2660, TP: 2680, SL: 2635\n"
    "  GOLD SELL 4678 - 4793, TP: 4671, SL: 4698\n\n"
    "This places TWO pending orders — one at each entry price — "
    "both with the same TP and SL.\n\n"
    "Commands:\n"
    "  /status  — MT5 connection, balance & equity\n"
    "  /trades  — last 5 executed trades\n"
    "  /help    — this message"
)


def _is_allowed(update: Update) -> bool:
    return update.effective_chat is not None and update.effective_chat.id == ALLOWED_CHAT_ID


def _log_trade(row: dict) -> None:
    path = Path(TRADES_CSV)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["timestamp", "action", "symbol", "entry_price", "tp", "sl", "lot", "status", "ticket", "error"],
        )
        if write_header:
            writer.writeheader()
        writer.writerow(row)


async def post_init(application: Application) -> None:
    msg = trader.connect()
    logger.info("Startup MT5: %s", msg)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return
    await update.message.reply_text(trader.get_status())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return
    await update.message.reply_text(HELP_TEXT)


async def cmd_trades(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return

    path = Path(TRADES_CSV)
    if not path.exists():
        await update.message.reply_text("No trades logged yet.")
        return

    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = deque(reader, maxlen=5)

    if not rows:
        await update.message.reply_text("No trades logged yet.")
        return

    lines = ["Last trades:"]
    for r in rows:
        status = r.get("status", "?")
        ticket = r.get("ticket", "")
        error = r.get("error", "")
        detail = f"#{ticket}" if ticket else error
        lines.append(
            f"{r.get('timestamp','')} | {r.get('action','')} @ {r.get('entry_price','')} "
            f"TP:{r.get('tp','')} SL:{r.get('sl','')} | {status} {detail}"
        )
    await update.message.reply_text("\n".join(lines))


async def handle_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Incoming message from chat_id: %s", update.effective_chat.id)
    if not _is_allowed(update):
        return

    text = (update.message.text or "").strip()
    match = ALERT_RE.match(text)

    if not match:
        if re.search(r"\b(BUY|SELL|GOLD)\b", text, re.IGNORECASE):
            await update.message.reply_text(
                "Unrecognised format. Expected:\n"
                "GOLD BUY 2650 - 2660, TP: 2680, SL: 2635"
            )
        return

    action = match.group(1).upper()
    price1 = float(match.group(2))
    price2 = float(match.group(3))
    tp = float(match.group(4))
    sl = float(match.group(5))

    status_msg = trader.get_status()
    if "Not connected" in status_msg or "not connected" in status_msg:
        logger.warning("MT5 disconnected — attempting reconnect")
        trader.connect()

    order_results, summary = trader.place_two_orders(action, price1, price2, tp, sl)

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for row in order_results:
        _log_trade({
            "timestamp": ts,
            "action": row["action"],
            "symbol": SYMBOL,
            "entry_price": row["entry_price"],
            "tp": row["tp"],
            "sl": row["sl"],
            "lot": 0.01,
            "status": row["status"],
            "ticket": row["ticket"],
            "error": row["error"],
        })

    await update.message.reply_text(summary)


async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("RAW UPDATE: %s", update)


def main() -> None:
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(MessageHandler(filters.ALL, log_all_updates), group=-1)
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("trades", cmd_trades))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alert))

    logger.info("Bot starting…")
    app.run_polling()


if __name__ == "__main__":
    main()
