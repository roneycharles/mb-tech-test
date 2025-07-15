import logging

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.withdraw import CreateWithdrawResponse, CreateWithdrawRequest, ListWithdrawalsResponse
from services.withdraw_service import WithdrawService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=CreateWithdrawResponse)
async def create_withdraw(request: CreateWithdrawRequest, db: AsyncSession = Depends(get_db)):
    logger.info("Creating withdraw via API")

    try:
        service = WithdrawService(db=db)
        response = await service.create_withdraw(request)

        logger.info("Withdraw created successfully via API")
        return response

    except ValueError as e:
        logger.error("Invalid withdraw request: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error("Database error creating withdraw: %s", e)
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error("Unexpected error creating withdraw: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=ListWithdrawalsResponse)
async def list_withdrawals(
        page: int = Query(1, gt=0, description="Current page number"),
        page_size: int = Query(50, gt=0, le=1000,description="Items per page (1 - 1000)"),
        db: AsyncSession = Depends(get_db)
):
    logger.info("Listing withdrawals via API: page=%d, page_size=%d", page, page_size)

    try:
        service = WithdrawService(db=db)
        response = await service.list_withdraws(page_size=page_size, page=page)

        logger.info("Successfully listed withdrawals via API")
        return response

    except SQLAlchemyError as e:
        logger.error("Database error listing withdrawals: %s", e)
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error("Unexpected error listing withdrawals: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")