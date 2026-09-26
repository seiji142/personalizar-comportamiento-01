from fastapi import APIRouter, HTTPException, Query, Depends, Header
from typing import Optional
import os

from ..models.payment import (
    CreatePaymentRequest,
    PaymentResponse,
    PaymentStatusResponse,
    PaymentStatus,
    RefundRequest,
    RefundResponse,
    ErrorResponse,
)
from ..services.payment_service import payment_service

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def verify_api_key(x_api_key: str = Header(...)) -> str:
    expected_key = os.getenv("PAYMENT_API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=201,
    summary="Create a new payment",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_payment(
    request: CreatePaymentRequest,
    api_key: str = Depends(verify_api_key),
) -> PaymentResponse:
    try:
        return payment_service.create_payment(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get payment details",
    responses={
        404: {"model": ErrorResponse, "description": "Payment not found"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def get_payment(
    payment_id: str,
    api_key: str = Depends(verify_api_key),
) -> PaymentResponse:
    try:
        return payment_service.get_payment(payment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{payment_id}/status",
    response_model=PaymentStatusResponse,
    summary="Get payment status",
    responses={
        404: {"model": ErrorResponse, "description": "Payment not found"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def get_payment_status(
    payment_id: str,
    api_key: str = Depends(verify_api_key),
) -> PaymentStatusResponse:
    try:
        return payment_service.get_payment_status(payment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "",
    response_model=list[PaymentResponse],
    summary="List payments",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def list_payments(
    customer_email: Optional[str] = Query(None, description="Filter by customer email"),
    status: Optional[PaymentStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Results offset"),
    api_key: str = Depends(verify_api_key),
) -> list[PaymentResponse]:
    return payment_service.list_payments(
        customer_email=customer_email,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{payment_id}/refund",
    response_model=RefundResponse,
    status_code=201,
    summary="Refund a payment",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid refund request"},
        404: {"model": ErrorResponse, "description": "Payment not found"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def refund_payment(
    payment_id: str,
    request: RefundRequest,
    api_key: str = Depends(verify_api_key),
) -> RefundResponse:
    try:
        return payment_service.refund_payment(payment_id, request)
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentResponse,
    summary="Cancel a pending payment",
    responses={
        400: {"model": ErrorResponse, "description": "Cannot cancel payment"},
        404: {"model": ErrorResponse, "description": "Payment not found"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def cancel_payment(
    payment_id: str,
    api_key: str = Depends(verify_api_key),
) -> PaymentResponse:
    try:
        return payment_service.cancel_payment(payment_id)
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))


@router.post(
    "/webhook",
    status_code=200,
    summary="Payment webhook endpoint",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid webhook data"},
    },
)
async def payment_webhook(
    payment_id: str = Header(..., alias="X-Payment-ID"),
    signature: str = Header(..., alias="X-Signature"),
    amount: float = Header(..., alias="X-Amount"),
    currency: str = Header(..., alias="X-Currency"),
) -> dict:
    webhook_secret = os.getenv("WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    if not payment_service.verify_payment_signature(
        payment_id, amount, currency, signature, webhook_secret
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")

    return {"status": "received"}
