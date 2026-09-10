from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    UYU = "UYU"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"


class CardInfo(BaseModel):
    number: str = Field(..., min_length=13, max_length=19, description="Card number")
    holder_name: str = Field(..., min_length=2, max_length=100, description="Cardholder name")
    expiry_month: int = Field(..., ge=1, le=12, description="Expiry month (1-12)")
    expiry_year: int = Field(..., ge=2024, le=2035, description="Expiry year")
    cvv: str = Field(..., min_length=3, max_length=4, description="CVV code")

    @field_validator("number")
    @classmethod
    def validate_card_number(cls, v: str) -> str:
        cleaned = re.sub(r"[\s-]", "", v)
        if not cleaned.isdigit():
            raise ValueError("Card number must contain only digits")
        if len(cleaned) < 13 or len(cleaned) > 19:
            raise ValueError("Invalid card number length")
        if not luhn_check(cleaned):
            raise ValueError("Invalid card number")
        return cleaned

    @field_validator("cvv")
    @classmethod
    def validate_cvv(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("CVV must contain only digits")
        return v


def luhn_check(card_number: str) -> bool:
    digits = [int(d) for d in card_number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(divmod(d * 2, 10))
    return total % 10 == 0


class CreatePaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, le=1000000, description="Payment amount")
    currency: Currency = Field(default=Currency.USD, description="Currency code")
    description: str = Field(..., min_length=1, max_length=500, description="Payment description")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    card_info: Optional[CardInfo] = Field(None, description="Card information (required for card payments)")
    customer_email: str = Field(..., description="Customer email address")
    customer_name: str = Field(..., min_length=2, max_length=100, description="Customer name")
    reference_id: Optional[str] = Field(None, max_length=100, description="External reference ID")
    metadata: Optional[dict] = Field(None, description="Additional metadata")

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("card_info")
    @classmethod
    def validate_card_info(cls, v: Optional[CardInfo], info) -> Optional[CardInfo]:
        payment_method = info.data.get("payment_method")
        if payment_method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD] and v is None:
            raise ValueError("Card information is required for card payments")
        return v


class PaymentResponse(BaseModel):
    id: str = Field(..., description="Unique payment identifier")
    amount: float = Field(..., description="Payment amount")
    currency: Currency = Field(..., description="Currency code")
    status: PaymentStatus = Field(..., description="Payment status")
    description: str = Field(..., description="Payment description")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    customer_email: str = Field(..., description="Customer email")
    customer_name: str = Field(..., description="Customer name")
    reference_id: Optional[str] = Field(None, description="External reference ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    metadata: Optional[dict] = Field(None, description="Additional metadata")
    card_last_four: Optional[str] = Field(None, description="Last four digits of card")


class PaymentStatusResponse(BaseModel):
    id: str = Field(..., description="Payment identifier")
    status: PaymentStatus = Field(..., description="Current payment status")
    amount: float = Field(..., description="Payment amount")
    currency: Currency = Field(..., description="Currency code")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class RefundRequest(BaseModel):
    amount: Optional[float] = Field(None, gt=0, description="Refund amount (None for full refund)")
    reason: str = Field(..., min_length=10, max_length=500, description="Refund reason")


class RefundResponse(BaseModel):
    id: str = Field(..., description="Refund identifier")
    payment_id: str = Field(..., description="Original payment identifier")
    amount: float = Field(..., description="Refund amount")
    status: str = Field(..., description="Refund status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Refund timestamp")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[dict] = Field(None, description="Additional error details")
