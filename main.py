import csv
import logging
import os
import re
from collections import deque
from datetime import datetime, timezone
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

_HEADER_RE = re.compile(r"GOLD\s+(BUY|SELL)\s+([\d.]+)\s*-\s*([\d.]+)", re.IGNORECASE)
_TP_RE = re.compile(r"TP\s*:\s*([\d.]+)", re.IGNORECASE)
_SL_RE = re.compile(r"SL\s*:\s*([\d.]+)", re.IGNORECASE)


def _parse_alert(text: str):
    header = _HEADER_RE.search(text)
    if not header:
        return None

    action = header.group(1).upper()
    price1 = float(header.group(2))
    price2 = float(header.group(3))

    tp_matches = _TP_RE.findall(text)
    if not tp_matches:
        return None
    tp = float(tp_matches[0])

    sl_match = _SL_RE.search(text)
    if not sl_match:
        return None
    sl = float(sl_match.group(1))

    return action, price1, price2, tp, sl


HELP_TEXT = (
    "MetaTrader5 GOLD Trading Bot\n\n"
    "Alert format:\n"
    "  ♾ 🥇 GOLD SELL 4676 - 4781\n"
    "  ➡️TP : 4669\n"
    "  ➡️TP : 4656\n"
    "  ➡️TP : OPEN\n"
    "  ⛔️SL : 4696\n\n"
    "Uses the FIRST TP and the SL. Extra TPs and OPEN are ignored.\n"
    "Places TWO pending orders — one at each entry price.\n\n"
    "Commands:\n"
    "  /status  — MT5 connection, balance & equity\n"
    "  /open    — current open positions & pending orders\n"
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


async def log_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat:
        logger.info("Incoming update — chat_id: %s | type: %s | name: %s",
                    chat.id, chat.type, chat.title or chat.first_name or "N/A")


async def cmd_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return
    await update.message.reply_text(trader.get_open_trades())


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
    if not _is_allowed(update):
        return

    text = (update.message.text or "").strip()
    parsed = _parse_alert(text)

    if not parsed:
        if re.search(r"\b(BUY|SELL|GOLD)\b", text, re.IGNORECASE):
            await update.message.reply_text(
                "Unrecognised format. Expected:\n"
                "♾ 🥇 GOLD SELL 4676 - 4781\n"
                "➡️TP : 4669\n"
                "⛔️SL : 4696"
            )
        return

    action, price1, price2, tp, sl = parsed

    status_msg = trader.get_status()
    if "Not connected" in status_msg or "not connected" in status_msg:
        logger.warning("MT5 disconnected — attempting reconnect")
        trader.connect()

    order_results, summary = trader.place_two_orders(action, price1, price2, tp, sl)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
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


def main() -> None:
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(MessageHandler(filters.ALL, log_chat_id), group=-1)
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("trades", cmd_trades))
    app.add_handler(CommandHandler("open", cmd_open))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alert))

    logger.info("Bot starting…")
    app.run_polling()


if __name__ == "__main__":
    main()
