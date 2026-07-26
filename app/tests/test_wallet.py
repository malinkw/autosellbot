"""Тесты кошелька: начисления, списания, защита баланса."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.exceptions import InsufficientFundsError, ValidationError
from app.models.enums import TransactionType
from app.services.wallet import WalletService
from app.tests.conftest import make_user


async def test_credit_increases_balance(session) -> None:  # type: ignore[no-untyped-def]
    user = await make_user(session, telegram_id=10)
    wallet = WalletService(session)
    tx = await wallet.credit(user.id, Decimal("500"), type_=TransactionType.TOPUP)
    assert tx.balance_after == Decimal("500.00")
    assert user.balance == Decimal("500.00")


async def test_debit_insufficient_funds(session) -> None:  # type: ignore[no-untyped-def]
    user = await make_user(session, telegram_id=11, balance=Decimal("100"))
    wallet = WalletService(session)
    with pytest.raises(InsufficientFundsError):
        await wallet.debit(user.id, Decimal("150"), type_=TransactionType.PURCHASE)
    assert user.balance == Decimal("100.00")


async def test_zero_amount_rejected(session) -> None:  # type: ignore[no-untyped-def]
    user = await make_user(session, telegram_id=12)
    wallet = WalletService(session)
    with pytest.raises(ValidationError):
        await wallet.apply(user.id, type_=TransactionType.MANUAL, amount=Decimal("0"))


async def test_balance_after_is_consistent(session) -> None:  # type: ignore[no-untyped-def]
    user = await make_user(session, telegram_id=13, balance=Decimal("200"))
    wallet = WalletService(session)
    await wallet.credit(user.id, Decimal("50"), type_=TransactionType.TOPUP)
    tx = await wallet.debit(user.id, Decimal("100"), type_=TransactionType.PURCHASE)
    assert tx.balance_after == Decimal("150.00")
    assert user.balance == Decimal("150.00")
