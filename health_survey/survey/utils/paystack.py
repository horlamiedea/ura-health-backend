import json
import time
import decimal
from typing import Any, Dict, Optional
from urllib import request, error

from django.conf import settings


PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/{reference}"


def _get_secret_key() -> str:
    key = getattr(settings, "PAYSTACK_SECRET_KEY", "") or ""
    if not key:
        raise RuntimeError("PAYSTACK_SECRET_KEY not configured.")
    return key


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_secret_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _amount_to_kobo(amount: Any) -> int:
    """
    Convert NGN amount to kobo expected by Paystack.
    Accepts str/float/Decimal.
    """
    if isinstance(amount, decimal.Decimal):
        amt = amount
    else:
        try:
            amt = decimal.Decimal(str(amount))
        except Exception:
            raise ValueError("Invalid amount")
    # scale to kobo and round
    kobo = int((amt * 100).quantize(decimal.Decimal("1"), rounding=decimal.ROUND_HALF_UP))
    if kobo <= 0:
        raise ValueError("Amount must be positive")
    return kobo


def initialize_transaction(
    email: str,
    amount: Any,
    currency: str = "NGN",
    reference: Optional[str] = None,
    callback_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Initialize a Paystack transaction.
    Returns: {"ok": bool, "data": {...} or None, "error": "..." or None}
    """
    payload: Dict[str, Any] = {
        "email": email,
        "amount": _amount_to_kobo(amount),
        "currency": currency or "NGN",
    }
    if reference:
        payload["reference"] = reference
    if callback_url:
        payload["callback_url"] = callback_url
    if metadata:
        payload["metadata"] = metadata

    req = request.Request(PAYSTACK_INITIALIZE_URL, data=json.dumps(payload).encode("utf-8"), headers=_headers(), method="POST")
    try:
        with request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            status = bool(data.get("status"))
            return {"ok": status, "data": data.get("data"), "error": None if status else (data.get("message") or "Initialize failed")}
    except error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
            data = json.loads(body)
            msg = data.get("message") or str(e)
        except Exception:
            msg = str(e)
        return {"ok": False, "data": None, "error": msg}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}


def verify_transaction(reference: str) -> Dict[str, Any]:
    """
    Verify a Paystack transaction by reference.
    Returns: {"ok": bool, "data": {...} or None, "error": "..." or None}
    On success, data typically includes: {"status":"success","reference":"...","amount":12345,"currency":"NGN", ...}
    """
    if not reference:
        return {"ok": False, "data": None, "error": "Missing reference"}
    url = PAYSTACK_VERIFY_URL.format(reference=reference)
    req = request.Request(url, headers=_headers(), method="GET")
    try:
        with request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            ok = bool(data.get("status"))
            return {"ok": ok, "data": data.get("data"), "error": None if ok else (data.get("message") or "Verify failed")}
    except error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
            data = json.loads(body)
            msg = data.get("message") or str(e)
        except Exception:
            msg = str(e)
        return {"ok": False, "data": None, "error": msg}
    except Exception as e:
        return {"ok": False, "data": None, "error": str(e)}
