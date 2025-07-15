import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.address import CreateAddressesResponse, CreateAddressesRequest, ListAddressesResponse
from services.address_service import AddressService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=CreateAddressesResponse)
async def create_addresses(request: CreateAddressesRequest, db: AsyncSession = Depends(get_db)):
    logger.info("Creating %d addresses via API", request.quantity)

    try:
        service = AddressService(db=db)
        response = await service.create_addresses(request)

        logger.info("Successfully created %d addresses via API", response.total_created)
        return response

    except ValueError as e:
        logger.error("Invalid address creation request: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        logger.error("Database error creating addresses: %s", e)
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error("Unexpected error creating addresses: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=ListAddressesResponse)
async def list_addresses(
        page_size: int = Query(50, gt=0, le=1000,description="Items per page (1 - 1000)"),
        page: int = Query(1, gt=0, description="Current page number"),
        db: AsyncSession = Depends(get_db)
):
    logger.info("Listing addresses via API: page=%d, page_size=%d", page, page_size)

    try:
        service = AddressService(db=db)
        response = await service.list_addresses(page_size=page_size, page=page)

        logger.info("Successfully listed addresses via API")
        return response
    except SQLAlchemyError as e:
        logger.error("Database error listing addresses: %s", e)
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error("Unexpected error listing addresses: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")