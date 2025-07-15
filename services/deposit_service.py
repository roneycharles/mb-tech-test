import logging
from typing import List, Dict

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from schemas.deposit import (
    CreateDepositRequest,
    CreateDepositResponse, ListDepositsResponse, DepositStatus, Deposit, DepositInDB
)

from models.deposit import Deposit as DBDeposit

from services.address_service import AddressService
from services.blockchain_service import BlockchainService

logger = logging.getLogger(__name__)

class DepositService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.address_service = AddressService(db)
        self.blockchain_service = BlockchainService(db)

    async def create_deposit(self, request: CreateDepositRequest) -> CreateDepositResponse:
        logger.info(f"Creating deposit for tx hash: {request.tx_hash}")

        try:
            tx_data = await self.blockchain_service.get_transaction_data(request.tx_hash)
            if not tx_data:
                return CreateDepositResponse(
                    tx_hash=request.tx_hash,
                    is_valid=False,
                    deposits=[],
                    message="Transaction not found on blockchain",
                )

            if not await self.blockchain_service.check_transaction_security(tx_data):
                logger.error("Transaction failed on blockchain or doesn't have enough confirmations: %s", request.tx_hash)
                return CreateDepositResponse(
                    tx_hash=request.tx_hash,
                    is_valid=False,
                    deposits=[],
                    message=f"Transaction failed on blockchain or doesn't have enough confirmations",
                )

            deposit_transfers = await self._process_deposit_transfers(tx_hash=request.tx_hash, tx_data=tx_data)
            if not deposit_transfers:
                return CreateDepositResponse(
                    tx_hash=request.tx_hash,
                    is_valid=False,
                    deposits=[],
                    message="No deposits to ours addresses found",
                )

            deposits_db: List[DepositInDB] = []
            failed_deposits = 0

            for deposit in deposit_transfers:
                try:
                    deposit_db = await self._save_deposit_on_db(deposit)
                    if deposit_db:
                        deposits_db.append(deposit_db)
                    else:
                        failed_deposits += 1
                        continue
                except Exception as e:
                    logger.error("Failed to save deposit: %s", e)
                    failed_deposits += 1
                    continue

            if failed_deposits > 0:
                logger.warning("Failed to save %d deposits to database", failed_deposits)

            if not deposits_db:
                return CreateDepositResponse(
                    tx_hash=request.tx_hash,
                    is_valid=True,
                    deposits=[],
                    message="Failed to save deposits on database",
                )

            logger.info("Successfully created %d deposits for tx hash: %s", len(deposit_transfers), request.tx_hash)

            return CreateDepositResponse(
                tx_hash=request.tx_hash,
                is_valid=True,
                deposits=deposits_db,
                message="Deposit successfully created",
            )
        except Exception as e:
            logger.error("Failed to create deposit for tx hash %s: %s", request.tx_hash, e)
            return CreateDepositResponse(
                tx_hash=request.tx_hash,
                is_valid=False,
                deposits=[],
                message="Internal error creating deposit",
            )

    async def _process_deposit_transfers(self, tx_hash: str, tx_data: Dict) -> List[Deposit]:
        try:
            transfers = await self.blockchain_service.get_transaction_transfers(tx_data)
            if not transfers:
                logger.error("No transfers found in transaction: %s", tx_hash)
                return []

            confirmations = await self.blockchain_service.get_transaction_confirmations(tx_data['block_number'])
            if not confirmations:
                logger.error("Could not get confirmations for transaction: %s", tx_hash)
                return []

            deposits: List[Deposit] = []
            addresses = [transfer.to_address for transfer in transfers]
            addresses_map = await self.address_service.get_addresses_ids_batch(addresses)

            for transfer in transfers:
                address_id = addresses_map.get(transfer.to_address)
                if not address_id:
                    logger.warning("Transfer not to your address: %s", transfer.to_address)
                    continue

                deposits.append(Deposit(
                    tx_hash=tx_hash,
                    status=DepositStatus.SUCCESS,
                    address_id=address_id,
                    from_address=transfer.from_address.lower(),
                    token_id=transfer.token_id,
                    amount=transfer.amount,
                    confirmations=confirmations,
                ))

                logger.info("Valid transfer found to address: %s ", transfer.to_address)

            if not deposits:
                logger.error("No deposits to ours addresses found for tx hash: %s", tx_hash)
                return []

            logger.info("Found %d valid deposits for tx hash: %s", len(deposits), tx_hash)

            return deposits
        except Exception as e:
            logger.error("Failed to process deposits transfers for tx hash %s: %s", tx_hash, e)
            return []

    async def _save_deposit_on_db(self, deposit: Deposit) -> DepositInDB:
        try:
            deposit_db = DBDeposit(
                tx_hash=deposit.tx_hash,
                status=deposit.status,
                address_id=deposit.address_id,
                from_address=deposit.from_address,
                token_id=deposit.token_id,
                amount=deposit.amount,
                confirmations=deposit.confirmations,
            )
            self.db.add(deposit_db)
            await self.db.flush()
            await self.db.commit()

            logger.info("Deposit saved to database: %s", deposit.tx_hash)
            return DepositInDB.model_validate(deposit_db)

        except SQLAlchemyError as e:
            logger.error("Database error saving deposit: %s", e)
            await self.db.rollback()
            raise
        except Exception as e:
            logger.error("Failed to save deposit on database: ", e)
            await self.db.rollback()
            raise

    async def list_deposits(self, page: int, page_size: int) -> ListDepositsResponse:
        logger.info("Listing deposits: page=%d, page_size=%d", page, page_size)

        try:
            select_total = select(func.count(DBDeposit.id))
            total_result = await self.db.execute(select_total)
            total = total_result.scalar() or 0

        except SQLAlchemyError as e:
            logger.error("Failed to count deposits: %s", e)
            return ListDepositsResponse(
                deposits=[],
                total=0,
                page=page,
                page_size=page_size,
                message="Database error while counting deposits",
            )

        if total == 0:
            logger.info("No deposits found on database")
            return ListDepositsResponse(
                deposits=[],
                total=0,
                page=page,
                page_size=page_size,
                message="No deposits found",
            )

        max_pages = (total + page_size - 1) // page_size
        if page > max_pages:
            logger.warning("Page %d exceeds max pages %d, using last page", page, max_pages)
            page = max_pages

        try:
            offset = (page - 1) * page_size
            query = (
                select(DBDeposit)
                .offset(offset)
                .limit(page_size)
                .order_by(DBDeposit.created_at.desc())
            )

            result = await self.db.execute(query)
            deposits_db = result.scalars().all()

        except SQLAlchemyError as e:
            logger.error("Failed to fetch deposits: %s", e)
            return ListDepositsResponse(
                deposits=[],
                total=total,
                page=page,
                page_size=page_size,
                message="Database error while fetching deposits",
            )

        try:
            deposits = [
                DepositInDB.model_validate(deposit)
                for deposit in deposits_db
            ]

            logger.info("Successfully listed %d deposits (page %d of %d)", len(deposits), page, max_pages)
            return ListDepositsResponse(
                deposits=deposits,
                total=total,
                page=page,
                page_size=page_size,
                message="Deposits retrieved successfully",
            )

        except Exception as e:
            logger.error("Failed to serialize deposits: %s", e)
            return ListDepositsResponse(
                deposits=[],
                total=total,
                page=page,
                page_size=page_size,
                message="Error processing deposits data",
            )