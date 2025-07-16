import logging
from typing import List, Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql.dml import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_security_manager
from schemas.address import ListAddressesResponse, CreateAddressesRequest, CreateAddressesResponse, AddressInDB
from models.address import Address as DBAddress

logger = logging.getLogger(__name__)

class AddressService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.security_manager = get_security_manager()

    async def create_addresses(self, request: CreateAddressesRequest) -> CreateAddressesResponse:
        logger.info("Creating new %d addresses", request.quantity)

        try:
            addresses_data = []
            for i in range(request.quantity):
                try:
                    address, private_key = self.security_manager.generate_account()
                    encrypted_key = self.security_manager.encrypt_private_key(private_key)

                    addresses_data.append({
                        'address': address.lower(),
                        'private_key': encrypted_key,
                    })

                except Exception as e:
                    logger.error("Failed to generate address %d: %s", (i + 1), e)
                    continue

            generated_count = len(addresses_data)
            generation_failures = request.quantity - generated_count

            if generation_failures > 0:
                logger.warning("Failed to generate %d addresses", generation_failures)

            if not addresses_data:
                raise ValueError("No addresses could be generated")

            db_addresses = [
                {
                    'address': data['address'],
                    'private_key': data['private_key'],
                    'is_active': True,
                }
                for data in addresses_data
            ]

            query = insert(DBAddress).values(db_addresses)
            upsert = query.on_conflict_do_nothing(index_elements=['address']).returning(DBAddress.id)

            result = await self.db.execute(upsert)
            created_count = len(result.fetchall())

            await self.db.commit()

            creation_failures = generated_count - created_count

            total_failures = creation_failures + generation_failures
            logger.info("Address creation completed: Created: %d - Failures: %d", created_count, total_failures)

            if created_count == request.quantity:
                status = "success"
                message = f"Successfully created all {request.quantity} addresses"
            elif created_count > 0:
                status = "partial"
                message = f"Successfully created {created_count} addresses with {total_failures} failures"
            else:
                status = "failure"
                message = f"Failed to create any of the {request.quantity} addresses"

            return CreateAddressesResponse(
                status=status,
                total_created=created_count,
                message=message,
            )
        except ValueError as e:
            logger.error("Address creation failed: %s", e)
            await self.db.rollback()
            raise
        except SQLAlchemyError as e:
            logger.error("Database error during address creation: %s", e)
            await self.db.rollback()
            raise
        except Exception as e:
            logger.error("Unexpected error during address creation: %s", e)
            await self.db.rollback()
            raise

    async def list_addresses(self, page: int, page_size: int) -> ListAddressesResponse:
        logger.info("Listing all addresses: page=%d, page_size=%d", page, page_size)

        try:
            select_total = select(func.count(DBAddress.id))
            total_result = await self.db.execute(select_total)
            total = total_result.scalar() or 0

        except SQLAlchemyError as e:
            logger.error("Failed to count addresses: %s", e)
            return ListAddressesResponse(
                addresses=[],
                total=0,
                page=page,
                page_size=page_size,
                message="Database error while counting addresses",
            )

        if total == 0:
            logger.info("No addresses found")
            return ListAddressesResponse(
                addresses=[],
                total=0,
                page=page,
                page_size=page_size,
                message="No addresses found",
            )

        max_pages = (total + page_size - 1) // page_size
        if page > max_pages:
            logger.warning("Page %d exceeds max pages %d, returning last page", page, max_pages)
            page = max_pages

        try:
            offset = (page - 1) * page_size
            query = (
                select(DBAddress)
                .offset(offset)
                .limit(page_size)
                .order_by(DBAddress.created_at.desc())
            )

            result = await self.db.execute(query)
            addresses_db = result.scalars().all()

        except SQLAlchemyError as e:
            logger.error("Failed to fetch addresses: %s", e)
            return ListAddressesResponse(
                addresses=[],
                total=total,
                page=page,
                page_size=page_size,
                message="Database error while fetching addresses",
            )

        try:
            addresses = [
                AddressInDB.model_validate(address)
                for address in addresses_db
            ]

            logger.info("Successfully listed %d addresses", len(addresses))
            return ListAddressesResponse(
                addresses=addresses,
                total=total,
                page=page,
                page_size=page_size,
                message="Addresses retrieved successfully",
            )
        except Exception as e:
            logger.error("Failed to serialize addresses: %s", e)
            return ListAddressesResponse(
                addresses=[],
                total=total,
                page=page,
                page_size=page_size,
                message="Error processing addresses data",
            )

    async def get_address_by_id(self, address_id: int, is_active: Optional[bool] = None) -> AddressInDB:
        try:
            query = select(DBAddress).where(DBAddress.id == address_id)

            if is_active is not None:
                query = query.where(DBAddress.is_active.is_(is_active))

            result = await self.db.execute(query)
            address_db = result.scalar()
            if not address_db:
                raise ValueError(f"Address not found with id: {address_id}")

            logger.info("Retrieved Address by id: %d", address_id)

            return AddressInDB.model_validate(address_db)
        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error("Database error getting address by id %d: %s", address_id, e)
            raise
        except Exception as e:
            logger.error("Unexpected error getting address by id %d: %s", address_id, e)
            raise

    async def get_address_id(self, address: str, is_active: Optional[bool] = None) -> int:
        try:
            query = select(DBAddress.id).where(DBAddress.address == address.lower())

            if is_active is not None:
                query = query.where(DBAddress.is_active.is_(is_active))

            result = await self.db.execute(query)
            address_id = result.scalar()
            if not address_id:
                raise ValueError(f"Address id not found for: {address}")

            logger.info("Retrieved Address by id %d for: %s", address_id, address)
            return address_id
        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error("Database error getting address id for %s: %s", address, e)
            raise
        except Exception as e:
            logger.error("Unexpected error getting address id for %s: %s", address, e)
            raise

    async def get_decrypted_private_key(self, address: str, is_active: Optional[bool] = None) -> str:
        try:
            query = select(DBAddress.private_key).where(DBAddress.address == address.lower())

            if is_active is not None:
                query = query.where(DBAddress.is_active.is_(is_active))

            result = await self.db.execute(query)
            private_key = result.scalar()
            if not private_key:
                raise ValueError(f"Private key not found for address: {address}")

            decrypted_key = self.security_manager.decrypt_private_key(private_key)
            logger.info("Retrieved and decrypted private Key for: %s", address)
            return decrypted_key
        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error("Database error getting private key for %s: %s", address, e)
            raise
        except Exception as e:
            logger.error("Error decrypting private key for %s: %s", address, e)
            raise

    async def get_addresses_ids_batch(self, addresses: List[str]) -> Dict[str, int]:
        try:
            unique_addresses = list(set(addr.lower() for addr in addresses))

            query = select(DBAddress.address, DBAddress.id).where(
                DBAddress.address.in_(unique_addresses),
                DBAddress.is_active == True,
            )

            result = await self.db.execute(query)
            addresses_db = result.fetchall()

            addresses_map = {address_db.address: address_db.id for address_db in addresses_db}

            found_count = len(addresses_map)
            not_found_count = len(unique_addresses) - found_count

            if not_found_count > 0:
                logger.warning("Batch lookup: Found: %d - Not Found: %d", found_count, not_found_count)
            else:
                logger.info("Batch lookup: found all %d addresses", found_count)

            return addresses_map
        except SQLAlchemyError as e:
            logger.error("Database error in batch address lookup: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error in batch address lookup: %s", e)
            raise