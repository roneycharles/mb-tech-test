import logging

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.deposit import CreateDepositRequest, CreateDepositResponse, ListDepositsResponse
from services.deposit_service import DepositService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=CreateDepositResponse)
async def create_deposit(request: CreateDepositRequest, db: AsyncSession = Depends(get_db)):
    logger.info("Creating deposit via API for tx hash: %s", request.tx_hash)

    try:
        service = DepositService(db=db)
        response = await service.create_deposit(request)

        logger.info("Deposit created successfully via API for tx hash: %s", request.tx_hash)
        return response

    except ValueError as e:
        logger.error("Invalid deposit request for tx hash %s: %s", request.tx_hash, e)
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error("Database error creating deposit with tx hash %s: %s", request.tx_hash, e)
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error("Unexpected error creating deposit for tx hash %s: %s", request.tx_hash, e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=ListDepositsResponse)
async def list_deposits(
        page_size: int = Query(50, gt=0, le=1000, description="Items per page (1 - 1000)"),
        page: int = Query(1, gt=0, description="Current page number"),
        db: AsyncSession = Depends(get_db)
):
    try:
        logger.debug("Listing deposits via API: page=%d, page_size=%d", page, page_size)

        service = DepositService(db=db)
        response = await service.list_deposits(page_size=page_size, page=page)

        logger.debug("Successfully listed deposits via API")
        return response

    except SQLAlchemyError as e:
        logger.error("Database error listing deposits: %s", e)
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error("Unexpected error listing deposits: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")