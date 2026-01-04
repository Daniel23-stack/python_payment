"""API v1 router."""

from fastapi import APIRouter

from src.api.v1.endpoints import accounts, transactions, transfers

api_router = APIRouter()

api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(transfers.router, prefix="/transfers", tags=["transfers"])

