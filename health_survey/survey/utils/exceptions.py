from typing import Any, Optional
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status


def _format_error_detail(detail: Any) -> Any:
    """
    Recursively formats DRF error details into simple primitives for JSON.
    """
    if isinstance(detail, (list, tuple)):
        return [_format_error_detail(item) for item in detail]
    if isinstance(detail, dict):
        return {key: _format_error_detail(value) for key, value in detail.items()}
    return str(detail)


def custom_exception_handler(exc, context):
    """
    Wrap all errors in a consistent structure:
    {
        "status": "error",
        "message": "Human-friendly summary",
        "errors": {...optional field-wise errors...}
    }
    """
    response: Optional[Response] = drf_exception_handler(exc, context)

    if response is None:
        # Non-DRF or unhandled exceptions
        return Response(
            {
                "status": "error",
                "message": "An unexpected error occurred.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = response.data
    message = "Validation error" if response.status_code == 400 else "Request failed"

    # Attempt to extract a human readable message
    if isinstance(data, dict):
        if "detail" in data:
            message = str(data.get("detail"))
            errors = None
        else:
            errors = _format_error_detail(data)
    else:
        errors = _format_error_detail(data)

    return Response(
        {
            "status": "error",
            "message": message,
            **({"errors": errors} if errors is not None else {}),
        },
        status=response.status_code,
    )
