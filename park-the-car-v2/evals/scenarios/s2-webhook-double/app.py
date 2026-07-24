"""Payment webhook handler (fixture). Seeded defects — see truth.json."""

ORDERS = []            # durable orders
PROCESSED = set()      # webhook ids we've handled
SERVER_PRICES = {"sku_basic": 4900, "sku_pro": 14900}


def handle_payment_webhook(payload: dict):
    """Provider calls this on successful charge. Provider retries any request
    that doesn't get a fast 200."""
    event_id = payload["event_id"]
    sku = payload["sku"]
    amount = payload["amount"]

    if event_id in PROCESSED:
        return {"ok": True, "dedup": True}

    # BUG-1 (seeded): amount is trusted from the webhook body instead of the
    # server price book — a tampered/foreign payload books a $1 pro plan.
    order = {"sku": sku, "amount": amount, "event": event_id}

    # simulate slow fulfilment (email receipt, provision account, etc.)
    _fulfil(order)          # takes seconds; provider may time out and retry

    ORDERS.append(order)
    # BUG-2 (seeded): PROCESSED is marked only after slow fulfilment with no
    # durable claim taken first — a provider retry that lands mid-fulfilment
    # passes the dedup check and double-creates the order. Also nothing here
    # is transactional: a crash after _fulfil but before append/mark leaves
    # a fulfilled-but-unrecorded order (BUG-3).
    PROCESSED.add(event_id)
    return {"ok": True}


def _fulfil(order):
    pass  # pretend: send receipt email, provision seat, notify ops
