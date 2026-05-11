import logging
import os
import MetaTrader5 as mt5
from config import LOT_SIZE, MAGIC_NUMBER, SYMBOL

logger = logging.getLogger(__name__)

RETCODE_MESSAGES = {
    10004: "Requote",
    10006: "Request rejected",
    10007: "Request cancelled by trader",
    10008: "Order placed",
    10009: "Request completed",
    10010: "Only part of the request was completed",
    10011: "Request processing error",
    10012: "Request cancelled by timeout",
    10013: "Invalid request",
    10014: "Invalid volume in the request",
    10015: "Invalid price in the request",
    10016: "Invalid stops in the request",
    10017: "Trade is disabled",
    10018: "Market is closed",
    10019: "Not enough money",
    10020: "Prices changed",
    10021: "No quotes to process the request",
    10022: "Invalid order expiration date",
    10023: "Order state changed",
    10024: "Too frequent requests",
    10025: "No changes in request",
    10026: "Autotrading disabled by server",
    10027: "Autotrading disabled by client terminal",
    10028: "Request locked for processing",
    10029: "Order or position frozen",
    10030: "Invalid order filling type",
    10031: "No connection with the trade server",
    10032: "Operation is allowed only for live accounts",
    10033: "The number of pending orders has reached the limit",
    10034: "The volume of orders and positions has reached the limit",
    10035: "Incorrect or prohibited order type",
    10036: "Position with the specified identifier already closed",
    10038: "Close volume exceeds the current position volume",
    10039: "A close order already exists for a specified position",
}

TRANSIENT_RETCODES = {10004, 10020, 10021}


def connect() -> str:
    login = int(os.environ["MT5_LOGIN"])
    password = os.environ["MT5_PASSWORD"]
    server = os.environ["MT5_SERVER"]

    if not mt5.initialize(login=login, password=password, server=server):
        error = mt5.last_error()
        logger.error("MT5 initialize failed: %s", error)
        return f"Failed to connect to MT5: {error}"

    info = mt5.account_info()
    if info is None:
        logger.error("MT5 connected but could not retrieve account info")
        return "Connected to MT5 but failed to retrieve account info."

    logger.info("Connected to MT5 — account %s, balance %.2f", info.login, info.balance)
    return f"Connected to MT5. Account: {info.login} | Balance: {info.balance:.2f} {info.currency}"


def disconnect() -> None:
    mt5.shutdown()
    logger.info("Disconnected from MT5")


def _ensure_symbol() -> bool:
    info = mt5.symbol_info(SYMBOL)
    if info is None:
        logger.error("Symbol %s not found", SYMBOL)
        return False
    if not info.visible:
        if not mt5.symbol_select(SYMBOL, True):
            logger.error("Could not enable symbol %s in MarketWatch", SYMBOL)
            return False
    return True


def _determine_order_type(action: str, entry_price: float) -> int | None:
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        logger.error("Could not get tick for %s", SYMBOL)
        return None

    current = tick.ask if action == "BUY" else tick.bid

    if action == "BUY":
        return mt5.ORDER_TYPE_BUY_LIMIT if entry_price < current else mt5.ORDER_TYPE_BUY_STOP
    else:
        return mt5.ORDER_TYPE_SELL_LIMIT if entry_price > current else mt5.ORDER_TYPE_SELL_STOP


def place_order(action: str, entry_price: float, tp: float, sl: float) -> tuple[bool, str]:
    if not _ensure_symbol():
        return False, f"Symbol {SYMBOL} not found or could not be enabled."

    order_type = _determine_order_type(action, entry_price)
    if order_type is None:
        return False, "Could not retrieve current price to determine order type."

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": SYMBOL,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": entry_price,
        "tp": tp,
        "sl": sl,
        "magic": MAGIC_NUMBER,
        "comment": "TelegramBot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    result = mt5.order_send(request)

    if result is None:
        logger.error("order_send returned None for entry %.2f", entry_price)
        return False, "order_send returned None — check MT5 connection."

    if result.retcode in TRANSIENT_RETCODES:
        logger.warning("Transient error %d for entry %.2f — retrying", result.retcode, entry_price)
        result = mt5.order_send(request)
        if result is None:
            logger.error("order_send returned None on retry for entry %.2f", entry_price)
            return False, "order_send returned None on retry — check MT5 connection."

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info("Order placed: ticket=%d entry=%.2f tp=%.2f sl=%.2f", result.order, entry_price, tp, sl)
        return True, str(result.order)

    desc = RETCODE_MESSAGES.get(result.retcode, f"Unknown retcode {result.retcode}")
    logger.error("Order failed for entry %.2f: [%d] %s", entry_price, result.retcode, desc)
    return False, f"[{result.retcode}] {desc}"


def place_two_orders(action: str, price1: float, price2: float, tp: float, sl: float) -> tuple[list[dict], str]:
    results = []
    lines = []

    for price in (price1, price2):
        ok, detail = place_order(action, price, tp, sl)
        results.append({
            "action": action,
            "entry_price": price,
            "tp": tp,
            "sl": sl,
            "status": "OK" if ok else "FAILED",
            "ticket": detail if ok else "",
            "error": "" if ok else detail,
        })
        if ok:
            lines.append(f"Entry {price:.2f} → Order #{detail} placed")
        else:
            lines.append(f"Entry {price:.2f} → FAILED: {detail}")

    return results, "\n".join(lines)


def get_status() -> str:
    if not mt5.terminal_info():
        return "MT5 is not connected."

    info = mt5.account_info()
    if info is None:
        return "MT5 connected but failed to retrieve account info."

    return (
        f"MT5 Status: Connected\n"
        f"Account:  {info.login}\n"
        f"Server:   {info.server}\n"
        f"Balance:  {info.balance:.2f} {info.currency}\n"
        f"Equity:   {info.equity:.2f} {info.currency}\n"
        f"Margin:   {info.margin:.2f} {info.currency}\n"
        f"Free:     {info.margin_free:.2f} {info.currency}"
    )
