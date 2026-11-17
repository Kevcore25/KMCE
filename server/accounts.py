"""KCash account endpoints."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field
from sqlalchemy import case, func
from sqlmodel import Session, select

from server import config
from server.db import Account, LedgerEntry, SessionDep, utcnow
from server.security import ClientDep, require_trusted_client

router = APIRouter(
    prefix="/v1/accounts",
    tags=["accounts"],
    dependencies=[Depends(require_trusted_client)],
)

Username = Annotated[str, Path(pattern=config.USERNAME_PATTERN)]


class Result(BaseModel):
    success: bool
    output: int | None = None
    reason: str | None = None


class DepositIn(BaseModel):
    amount: int = Field(ge=0)


class WithdrawIn(BaseModel):
    amount: int = Field(gt=0)


def _get_or_create(session: Session, username: str) -> Account:
    account = session.get(Account, username)
    if account is None:
        account = Account(username=username)
        session.add(account)
    return account


def _record(
    session: Session, request: Request, server_id: str, account: Account, kind: str, amount: int
) -> None:
    session.add(
        LedgerEntry(
            username=account.username,
            kind=kind,
            amount=amount,
            balance_after=account.bal,
            server_id=server_id,
            client_ip=request.client.host if request.client else None,
        )
    )


def _recent_gain(session: Session, username: str, server_id: str) -> int:
    """Net KCash gained by a player on one server within the gain window."""
    cutoff = utcnow() - timedelta(minutes=config.GAIN_WINDOW_MINUTES)
    signed = case(
        (LedgerEntry.kind == "deposit", LedgerEntry.amount),
        (LedgerEntry.kind == "transfer", -LedgerEntry.amount),
        else_=0,
    )
    statement = select(func.coalesce(func.sum(signed), 0)).where(
        LedgerEntry.username == username,
        LedgerEntry.server_id == server_id,
        LedgerEntry.created_at >= cutoff,
    )
    return session.exec(statement).one()


@router.get("/{username}/balance", response_model_exclude_none=True)
def get_balance(username: Username, session: SessionDep) -> Result:
    account = session.get(Account, username)
    return Result(success=True, output=account.bal if account else 0)


@router.post("/{username}/deposit", response_model_exclude_none=True)
def deposit(
    username: Username, body: DepositIn, request: Request, session: SessionDep, client: ClientDep
) -> Result:
    if config.GAIN_LIMIT > 0 and body.amount > 0:
        gained = _recent_gain(session, username, client)
        if gained + body.amount > config.GAIN_LIMIT:
            remaining = max(config.GAIN_LIMIT - gained, 0)
            raise HTTPException(
                status_code=429,
                detail=f"Gain limit reached, you can only save {remaining} more KCash on this server for now",
            )

    account = _get_or_create(session, username)
    account.bal = min(account.bal + body.amount, config.MAX_BALANCE)
    _record(session, request, client, account, "deposit", body.amount)
    session.commit()
    return Result(success=True, output=account.bal)


@router.post("/{username}/withdraw", response_model_exclude_none=True)
def withdraw(
    username: Username, body: WithdrawIn, request: Request, session: SessionDep, client: ClientDep
) -> Result:
    account = session.get(Account, username)
    if account is None or account.bal < body.amount:
        raise HTTPException(status_code=409, detail="Insufficient balance")
    account.bal -= body.amount
    _record(session, request, client, account, "withdraw", body.amount)
    session.commit()
    return Result(success=True, output=account.bal)


@router.post("/{username}/transfer", response_model_exclude_none=True)
def transfer(username: Username, request: Request, session: SessionDep, client: ClientDep) -> Result:
    """Empties the global balance and returns what it was, to be added locally."""
    account = _get_or_create(session, username)
    previous = account.bal
    account.bal = 0
    _record(session, request, client, account, "transfer", previous)
    session.commit()
    return Result(success=True, output=previous)
