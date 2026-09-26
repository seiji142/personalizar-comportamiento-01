import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
import hashlib
import hmac
import json

from ..models.payment import (
    CreatePaymentRequest,
    PaymentResponse,
    PaymentStatus,
    PaymentStatusResponse,
    RefundRequest,
    RefundResponse,
)


class PaymentService:
    def __init__(self):
        self._payments: Dict[str, Dict[str, Any]] = {}
        self._refunds: Dict[str, Dict[str, Any]] = {}

    def create_payment(self, request: CreatePaymentRequest) -> PaymentResponse:
        payment_id = str(uuid.uuid4())
        now = datetime.utcnow()

        card_last_four = None
        if request.card_info:
            card_last_four = request.card_info.number[-4:]

        payment_data = {
            "id": payment_id,
            "amount": request.amount,
            "currency": request.currency,
            "status": PaymentStatus.PENDING,
            "description": request.description,
            "payment_method": request.payment_method,
            "customer_email": request.customer_email,
            "customer_name": request.customer_name,
            "reference_id": request.reference_id,
            "metadata": request.metadata,
            "created_at": now,
            "updated_at": now,
            "card_last_four": card_last_four,
        }

        self._payments[payment_id] = payment_data

        self._process_payment(payment_id)

        return PaymentResponse(**self._payments[payment_id])

    def _process_payment(self, payment_id: str) -> None:
        payment = self._payments[payment_id]
        payment["status"] = PaymentStatus.PROCESSING
        payment["updated_at"] = datetime.utcnow()

        try:
            payment["status"] = PaymentStatus.COMPLETED
            payment["updated_at"] = datetime.utcnow()
        except Exception as e:
            payment["status"] = PaymentStatus.FAILED
            payment["updated_at"] = datetime.utcnow()
            payment["metadata"] = payment.get("metadata") or {}
            payment["metadata"]["error"] = str(e)

    def get_payment_status(self, payment_id: str) -> PaymentStatusResponse:
        if payment_id not in self._payments:
            raise ValueError(f"Payment {payment_id} not found")

        payment = self._payments[payment_id]
        return PaymentStatusResponse(
            id=payment["id"],
            status=payment["status"],
            amount=payment["amount"],
            currency=payment["currency"],
            created_at=payment["created_at"],
            updated_at=payment["updated_at"],
        )

    def get_payment(self, payment_id: str) -> PaymentResponse:
        if payment_id not in self._payments:
            raise ValueError(f"Payment {payment_id} not found")

        return PaymentResponse(**self._payments[payment_id])

    def list_payments(
        self,
        customer_email: Optional[str] = None,
        status: Optional[PaymentStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PaymentResponse]:
        results = list(self._payments.values())

        if customer_email:
            results = [p for p in results if p["customer_email"] == customer_email]

        if status:
            results = [p for p in results if p["status"] == status]

        results = sorted(results, key=lambda x: x["created_at"], reverse=True)

        paginated = results[offset : offset + limit]
        return [PaymentResponse(**p) for p in paginated]

    def refund_payment(self, payment_id: str, request: RefundRequest) -> RefundResponse:
        if payment_id not in self._payments:
            raise ValueError(f"Payment {payment_id} not found")

        payment = self._payments[payment_id]

        if payment["status"] != PaymentStatus.COMPLETED:
            raise ValueError(f"Cannot refund payment with status {payment['status']}")

        refund_amount = request.amount if request.amount else payment["amount"]

        if refund_amount > payment["amount"]:
            raise ValueError("Refund amount cannot exceed original payment amount")

        refund_id = str(uuid.uuid4())
        now = datetime.utcnow()

        refund_data = {
            "id": refund_id,
            "payment_id": payment_id,
            "amount": refund_amount,
            "status": "completed",
            "created_at": now,
            "reason": request.reason,
        }

        self._refunds[refund_id] = refund_data

        if refund_amount == payment["amount"]:
            payment["status"] = PaymentStatus.REFUNDED
        payment["updated_at"] = now

        return RefundResponse(
            id=refund_id,
            payment_id=payment_id,
            amount=refund_amount,
            status="completed",
            created_at=now,
        )

    def cancel_payment(self, payment_id: str) -> PaymentResponse:
        if payment_id not in self._payments:
            raise ValueError(f"Payment {payment_id} not found")

        payment = self._payments[payment_id]

        if payment["status"] not in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]:
            raise ValueError(f"Cannot cancel payment with status {payment['status']}")

        payment["status"] = PaymentStatus.CANCELLED
        payment["updated_at"] = datetime.utcnow()

        return PaymentResponse(**payment)

    def generate_payment_signature(
        self, payment_id: str, amount: float, currency: str, secret: str
    ) -> str:
        payload = f"{payment_id}:{amount}:{currency}"
        return hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def verify_payment_signature(
        self, payment_id: str, amount: float, currency: str, signature: str, secret: str
    ) -> bool:
        expected = self.generate_payment_signature(payment_id, amount, currency, secret)
        return hmac.compare_digest(expected, signature)


payment_service = PaymentService()
