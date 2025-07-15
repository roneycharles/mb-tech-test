import logging
from typing import Optional, List, Dict

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql.functions import func

from schemas.token import TokenType
from schemas.withdraw import CreateWithdrawRequest, CreateWithdrawResponse, WithdrawInDB, ListWithdrawalsResponse, \
    Withdraw, WithdrawStatus
from services.address_service import AddressService
from services.blockchain_service import BlockchainService
from models.withdraw import Withdraw as DBWithdraw
from services.token_service import TokenService

logger = logging.getLogger(__name__)

class WithdrawService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.address_service = AddressService(db)
        self.blockchain_service = BlockchainService(db)
        self.token_service = TokenService(db)

    async def create_withdraw(self, request: CreateWithdrawRequest) -> CreateWithdrawResponse:
        logger.info("Creating withdraw from address: %s", request.from_address)

        try:
            address_id = await self.address_service.get_address_id(address=request.from_address, is_active=True)
            if not address_id:
                logger.error("Invalid from address: %s", request.from_address)
                raise ValueError("From address is not ours")

            token_id = await self.token_service.get_token_id_by_symbol(symbol=request.symbol, is_active=True)
            if not token_id:
                logger.error("Invalid token symbol: %s", request.symbol)
                raise ValueError("Invalid token symbol")

            withdraw = Withdraw(
                status=WithdrawStatus.PENDING,
                address_id=address_id,
                to_address=request.to_address,
                token_id=token_id,
                amount=request.amount,
            )

            withdraw_db = await self._save_withdraw_on_db(withdraw)
            if not withdraw_db:
                logger.error("Failed to save withdraw on database")
                raise ValueError("Failed to save withdraw on database")

            logger.info("Withdraw created successfully with id: %s", withdraw_db.id)
            return CreateWithdrawResponse(
                withdraw=withdraw_db,
                message="Withdraw created successfully",
            )

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to create withdraw: %s", e)
            raise

    async def _save_withdraw_on_db(self, withdraw: Withdraw) -> WithdrawInDB:
        try:
            withdraw_db = DBWithdraw(
                status=withdraw.status,
                address_id=withdraw.address_id,
                to_address=withdraw.to_address.lower(),
                token_id=withdraw.token_id,
                amount=withdraw.amount,
            )

            self.db.add(withdraw_db)
            await self.db.flush()
            await self.db.commit()
            logger.info("Withdraw saved to database")
            return WithdrawInDB.model_validate(withdraw_db)

        except SQLAlchemyError as e:
            logger.error("Database error saving withdraw: %s", e)
            await self.db.rollback()
            raise
        except Exception as e:
            logger.error("Failed to save withdraw: ", e)
            await self.db.rollback()
            raise

    async def list_withdraws(self, page: int, page_size: int) -> ListWithdrawalsResponse:
        logger.info("Listing withdrawals: page=%d, page_size=%d", page, page_size)

        try:
            select_total = select(func.count(DBWithdraw.id))
            total_result = await self.db.execute(select_total)
            total = total_result.scalar() or 0

        except SQLAlchemyError as e:
            logger.error("Failed to count withdrawals: %s", e)
            return ListWithdrawalsResponse(
                withdrawals=[],
                total=0,
                page=page,
                page_size=page_size,
                message="Database error while counting withdrawals",
            )

        if total == 0:
            logger.info("No withdrawals found on database")
            return ListWithdrawalsResponse(
                withdrawals=[],
                total=0,
                page=page,
                page_size=page_size,
                message="No withdrawals found",
            )

        max_pages = (total + page_size - 1) // page_size
        if page > max_pages:
            logger.warning("Page %d exceeds max pages %d, using last page", page, max_pages)
            page = max_pages

        try:
            offset = (page - 1) * page_size
            query = (
                select(DBWithdraw)
                .offset(offset)
                .limit(page_size)
                .order_by(DBWithdraw.created_at.desc())
            )

            result = await self.db.execute(query)
            withdrawals_db = result.scalars().all()

        except SQLAlchemyError as e:
            logger.error("Failed to fetch withdrawals: %s", e)
            return ListWithdrawalsResponse(
                withdrawals=[],
                total=total,
                page=page,
                page_size=page_size,
                message="Database error while fetching withdrawals",
            )

        try:
            withdrawals = [
                WithdrawInDB.model_validate(withdraw)
                for withdraw in withdrawals_db
            ]

            logger.info("Successfully listed %d withdrawals (page %d of %d)", len(withdrawals), page, max_pages)
            return ListWithdrawalsResponse(
                withdrawals=withdrawals,
                total=total,
                page=page,
                page_size=page_size,
                message="Withdrawals retrieved successfully",
            )

        except Exception as e:
            logger.error("Failed to serialize withdrawals: %s", e)
            return ListWithdrawalsResponse(
                withdrawals=[],
                total=total,
                page=page,
                page_size=page_size,
                message="Error processing withdrawal data",
            )

    async def get_withdraw_by_id(self, withdraw_id: int, status: Optional[WithdrawStatus] = None) -> WithdrawInDB:
        try:
            query = select(DBWithdraw).where(DBWithdraw.id == withdraw_id)

            if status is not None:
                query = query.where(DBWithdraw.status == status)

            result = await self.db.execute(query)
            withdraw_db = result.scalar()
            if not withdraw_db:
                raise ValueError(f"No withdrawal found with id {withdraw_id}")

            logger.info("Retrieved withdraw by id: %s", withdraw_id)
            return WithdrawInDB.model_validate(withdraw_db)

        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error("Database error getting withdraw by id %d: %s", withdraw_id, e)
            raise
        except Exception as e:
            logger.error("Unexpected error getting withdraw by id %d: %s", withdraw_id, e)
            raise

    async def get_withdrawals_by_status(self, status: WithdrawStatus) -> List[WithdrawInDB]:
        try:
            query = select(DBWithdraw).where(DBWithdraw.status == status).order_by(DBWithdraw.created_at.asc())

            result = await self.db.execute(query)
            withdrawals_db = result.scalars().all()
            if not withdrawals_db:
                logger.error("No withdrawals found with status %s", status)
                return []

            withdrawals = [
                WithdrawInDB.model_validate(withdraw)
                for withdraw in withdrawals_db
            ]

            logger.info("Found %d withdrawals with status: %s", len(withdrawals), status)
            return withdrawals

        except SQLAlchemyError as e:
            logger.error("Database error getting withdrawals by status %s: %s", status, e)
            raise
        except Exception as e:
            logger.error("Unexpected error getting withdrawals by status %s: %s", status, e)
            raise

    async def process_withdraw(self, withdraw: WithdrawInDB) -> bool:
        try:
            address = await self.address_service.get_address_by_id(address_id=withdraw.address_id, is_active=True)
            if not address:
                logger.error("Address not found for withdraw id: %d", withdraw.id)
                return False

            token = await self.token_service.get_token_by_id(token_id=withdraw.token_id, is_active=True)
            if not token:
                logger.error("Token not found for withdraw id: %d", withdraw.id)
                return False

            if token.type == TokenType.MAINCOIN:
                tx_params = await self.blockchain_service.build_eth_transaction(
                    from_address=address.address,
                    to_address=withdraw.to_address,
                    amount=withdraw.amount,
                )
            else:
                tx_params = await self.blockchain_service.build_token_transaction(
                    from_address=address.address,
                    to_address=withdraw.to_address,
                    token_address=token.address,
                    amount=withdraw.amount,
                    decimals=token.decimals,
                )

            decrypted_pk = await self.address_service.get_decrypted_private_key(address=address.address, is_active=True)
            if not decrypted_pk:
                logger.error("Failed to get private key for withdraw id: %d", withdraw.id)
                return False

            tx_hash = await self.blockchain_service.send_transaction(tx_params=tx_params, private_key=decrypted_pk)
            if not tx_hash:
                logger.error("Failed to send transaction for withdraw id: %d", withdraw.id)
                return False

            fields_to_update = {
                "tx_hash": tx_hash,
                "status": WithdrawStatus.IN_PROGRESS,
            }

            withdraw_db = await self._update_withdraw_on_db(withdraw.id, fields_to_update)
            if not withdraw_db:
                logger.error("Failed to update withdraw with id: %d", withdraw.id)
                return False

            logger.info("Successfully processed withdraw id %d, tx_hash: %s", withdraw.id, tx_hash)
            return True

        except Exception as e:
            logger.error("Failed to process withdraw with id %s: %s", withdraw.id, e)
            return False

    async def can_process_withdraw(self, address_id: int) -> bool:
        try:
            result = await self.db.execute(
                select(DBWithdraw).where(
                    DBWithdraw.address_id == address_id,
                    DBWithdraw.status == WithdrawStatus.IN_PROGRESS
                ).limit(1)
            )

            return result.scalar_one_or_none() is None

        except SQLAlchemyError as e:
            logger.error("Database error checking if can process withdraw for address_id %d: %s", address_id, e)
            return False
        except Exception as e:
            logger.error("Unexpected error checking if can process withdraw for address_id %d: %s", address_id, e)
            return False

    async def update_withdraw_status(self, withdraw: WithdrawInDB) -> bool:
        try:
            if not withdraw.tx_hash:
                logger.warning("Withdraw %d has no tx_hash, cannot update status", withdraw.id)
                return False

            tx_data = await self.blockchain_service.get_transaction_data(withdraw.tx_hash)
            if not tx_data:
                logger.warning("Transaction data not found for withdraw: %d", withdraw.id)
                return False

            receipt = tx_data["receipt"]
            fields_to_update = {}

            if not self._check_transaction_status(tx_data):
                if receipt["status"] == 0:
                    fields_to_update["status"] = WithdrawStatus.FAILED
                    withdraw_db = await self._update_withdraw_on_db(withdraw_id=withdraw.id, updates=fields_to_update)
                    if not withdraw_db:
                        logger.error("Error when try to update failed withdraw: %d", withdraw.id)
                        return False

                    logger.info("Withdraw %d marked as failed", withdraw.id)
                    return True

            confirmations = await self.blockchain_service.get_transaction_confirmations(tx_data['block_number'])
            if not confirmations:
                logger.warning("Could not get confirmations for withdraw: %d", withdraw.id)
                return False

            gas_cost = self.blockchain_service.calculate_gas_cost(tx_data)

            fields_to_update["status"] = WithdrawStatus.SUCCESS
            fields_to_update["confirmations"] = confirmations
            fields_to_update["gas_cost"] = gas_cost

            withdraw_db = await self._update_withdraw_on_db(withdraw.id, fields_to_update)
            if not withdraw_db:
                logger.info("Failed to update successful withdraw: %d", withdraw.id)
                return False

            logger.info("Withdraw %d marked as successful", withdraw.id)
            return True

        except Exception as e:
            logger.error("Failed to update withdraw status for id %d: %s", withdraw.id, e)
            return False

    async def _update_withdraw_on_db(self, withdraw_id, updates: Dict) -> Optional[WithdrawInDB]:
        try:
            query = update(DBWithdraw).where(
                DBWithdraw.id == withdraw_id
            ).values(**updates).returning(DBWithdraw)

            result = await self.db.execute(query)
            withdraw_db = result.scalar_one_or_none()

            if not withdraw_db:
                raise ValueError(f"Withdraw not found with id: {withdraw_id}")

            await self.db.commit()

            logger.info("Withdraw successfully updated: %d", withdraw_id)
            return WithdrawInDB.model_validate(withdraw_db)

        except ValueError:
            await self.db.rollback()
            raise
        except SQLAlchemyError as e:
            logger.error("Database error updating withdraw %d: %s", withdraw_id, e)
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Unexpected error updating withdraw %d: %s", withdraw_id, e)
            raise

    @staticmethod
    def _check_transaction_status(tx_data: Dict) -> bool:
        if not tx_data:
            logger.error("Transaction data is empty")
            raise ValueError("Transaction data is empty")

        try:
            status = tx_data['status']

            if not status:
                logger.error("Transaction status field is missing from transaction data")
                raise KeyError("'status' field is missing from transaction data")

            if status != 1:
                logger.warning("Transaction failed on blockchain with status: %s", status)
                return False
            else:
                return True

        except KeyError as e:
            logger.error("Invalid transaction data: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error checking transaction status: %s", e)
            raise