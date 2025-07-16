from unittest.mock import Mock, patch, AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from schemas.address import CreateAddressesRequest, AddressInDB
from services.address_service import AddressService

from models.address import Address as DBAddress


class TestAddressService:

    @pytest.fixture(autouse=True)
    def setup_service(self, mock_db_session):
        self.mock_security_manager = Mock()
        self.security_manager_patcher = patch('services.address_service.get_security_manager')
        self.mock_get_security_manager = self.security_manager_patcher.start()
        self.mock_get_security_manager.return_value = self.mock_security_manager

        self.service = AddressService(mock_db_session)
        self.db: AsyncMock = mock_db_session

        mock_db_session.reset_mock()

        yield

        self.security_manager_patcher.stop()

    @pytest.mark.asyncio
    async def test_create_addresses_success_total(self):
        request = CreateAddressesRequest(quantity=2)

        self.mock_security_manager.generate_account.side_effect = [
            ("0xaddress1", "pk_1"),
            ("0xaddress2", "pk_2"),
        ]
        self.mock_security_manager.encrypt_private_key.side_effect = [
            "encrypted_pk_1",
            "encrypted_pk_2",
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = [Mock(), Mock()]
        self.db.execute.return_value = mock_result

        response = await self.service.create_addresses(request)

        assert response.status == "success"
        assert response.total_created == 2
        assert response.message == "Successfully created all 2 addresses"

    @pytest.mark.asyncio
    async def test_create_addresses_success_partial(self):
        request = CreateAddressesRequest(quantity=3)

        self.mock_security_manager.generate_account.side_effect = [
            ("0xaddress1", "pk_1"),
            Exception("Failed to generate address"),
            ("0xaddress3", "pk_3"),
        ]
        self.mock_security_manager.encrypt_private_key.side_effect = [
            "encrypted_pk_1",
            "encrypted_pk_3",
        ]
        mock_result = Mock()
        mock_result.fetchall.return_value = [Mock(), Mock()]
        self.db.execute.return_value = mock_result

        response = await self.service.create_addresses(request)

        assert response.status == "partial"
        assert response.total_created == 2
        assert response.message == "Successfully created 2 addresses with 1 failures" in response.message

    @pytest.mark.asyncio
    async def test_create_addresses_failed_no_address_generated(self):
        request = CreateAddressesRequest(quantity=1)

        self.mock_security_manager.generate_account.side_effect = Exception("Failed to create address")

        with pytest.raises(ValueError, match="No addresses could be generated"):
            await self.service.create_addresses(request)

        self.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_addresses_failed_no_address_created(self):
        request = CreateAddressesRequest(quantity=1)

        self.mock_security_manager.generate_account.side_effect = [
            ("0xaddress1", "pk_1"),
        ]
        self.mock_security_manager.encrypt_private_key.side_effect = "encrypted_pk_1"

        mock_result = Mock()
        mock_result.fetchall.return_value = []
        self.db.execute.return_value = mock_result

        response = await self.service.create_addresses(request)

        assert response.status == "failure"
        assert response.total_created == 0
        assert "Failed to create any of the 1 addresses" in response.message

    @pytest.mark.asyncio
    async def test_create_addresses_failed_sqlalchemy_error(self):
        request = CreateAddressesRequest(quantity=1)

        self.mock_security_manager.generate_account.side_effect = [
            ("0xaddress1", "pk_1"),
        ]
        self.mock_security_manager.encrypt_private_key.side_effect = "encrypted_pk_1"

        self.db.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            await self.service.create_addresses(request)

        self.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_addresses_failed_unknown_error(self):
        request = CreateAddressesRequest(quantity=1)

        self.mock_security_manager.generate_account.side_effect = [
            ("0xaddress1", "pk_1"),
        ]
        self.mock_security_manager.encrypt_private_key.side_effect = "encrypted_pk_1"

        mock_result = Mock()
        mock_result.fetchall.return_value = [Mock()]
        self.db.execute.return_value = mock_result

        self.db.commit.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            await self.service.create_addresses(request)

        self.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_addresses_success(self):
        mock_page = 1
        mock_page_size = 10

        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 2

        mock_addresses = [
            Mock(spec=DBAddress),
            Mock(spec=DBAddress),
        ]
        mock_query_result = Mock()
        mock_query_result.scalars.return_value.all.return_value = mock_addresses
        self.db.execute.side_effect = [mock_count_result, mock_query_result]

        with patch("services.address_service.AddressInDB") as mock_address_schema:
            mock_address_schema.model_validate.side_effect = [
                Mock(spec=AddressInDB),
                Mock(spec=AddressInDB),
            ]
            response = await self.service.list_addresses(mock_page, mock_page_size)

        assert len(response.addresses) == 2
        assert response.total == 2
        assert response.page == 1
        assert response.page_size == 10
        assert response.message == "Addresses retrieved successfully"

    @pytest.mark.asyncio
    async def test_list_addresses_failed_addresses_not_found(self):
        mock_page = 1
        mock_page_size = 10

        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 0

        self.db.execute.return_value = mock_count_result

        response = await self.service.list_addresses(mock_page, mock_page_size)

        assert response.addresses == []
        assert response.total == 0
        assert response.message == "No addresses found"

        assert self.db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_list_addresses_success_page_exceed_max_pages(self):
        mock_page = 5
        mock_page_size = 10
        mock_total = 25

        mock_count_result = Mock()
        mock_count_result.scalar.return_value = mock_total

        mock_addresses = [
            Mock(spec=DBAddress),
        ]
        mock_query_result = Mock()
        mock_query_result.scalars.return_value.all.return_value = mock_addresses
        self.db.execute.side_effect = [mock_count_result, mock_query_result]

        with patch("services.address_service.AddressInDB") as mock_address_schema:
            mock_address_schema.model_validate.return_value = Mock(spec=AddressInDB)

            response = await self.service.list_addresses(mock_page, mock_page_size)

        assert response.page == 3
        assert response.total == mock_total
        assert response.message == "Addresses retrieved successfully"

    @pytest.mark.asyncio
    async def test_list_addresses_failed_count_addresses_sqlalchemy_error(self):
        mock_page = 1
        mock_page_size = 10

        self.db.execute.side_effect = SQLAlchemyError("Database error")

        response = await self.service.list_addresses(mock_page, mock_page_size)

        assert response.addresses == []
        assert response.total == 0
        assert response.message == "Database error while counting addresses"

    @pytest.mark.asyncio
    async def test_list_addresses_failed_fetching_addresses(self):
        mock_page = 1
        mock_page_size = 10
        mock_total = 12

        mock_count_result = Mock()
        mock_count_result.scalar.return_value = mock_total
        self.db.execute.side_effect = [
            mock_count_result,
            SQLAlchemyError("Database error"),
        ]

        response = await self.service.list_addresses(mock_page, mock_page_size)

        assert response.addresses == []
        assert response.total == mock_total
        assert response.message == "Database error while fetching addresses"

    @pytest.mark.asyncio
    async def test_list_addresses_failed_unknown_error(self):
        mock_page = 1
        mock_page_size = 10
        mock_total = 25

        mock_count_result = Mock()
        mock_count_result.scalar.return_value = mock_total

        mock_addresses = [
            Mock(spec=DBAddress),
        ]
        mock_query_result = Mock()
        mock_query_result.scalars.return_value.all.return_value = mock_addresses

        self.db.execute.side_effect = [mock_count_result, mock_query_result]

        with patch("services.address_service.AddressInDB") as mock_address_schema:
            mock_address_schema.model_validate.side_effect = Exception("Failed to serialize addresses")

            response = await self.service.list_addresses(mock_page, mock_page_size)

        assert response.addresses == []
        assert response.total == mock_total
        assert response.page == mock_page
        assert response.page_size == mock_page_size
        assert response.message == "Error processing addresses data"

    @pytest.mark.asyncio
    async def test_get_address_by_id_success(self):
        mock_address_id = 1
        expected_address = Mock(spec=AddressInDB)

        mock_result = Mock()
        mock_result.scalar.return_value = Mock(spec=DBAddress)
        self.db.execute.return_value = mock_result

        with patch("services.address_service.AddressInDB") as mock_address_schema:
            mock_address_schema.model_validate.return_value = expected_address

            response = await self.service.get_address_by_id(mock_address_id)

        assert response == expected_address

    @pytest.mark.asyncio
    async def test_get_address_by_id_success_with_is_active_filter(self):
        mock_address_id = 1
        mock_is_active = True
        expected_address = Mock(spec=AddressInDB)

        mock_result = Mock()
        mock_result.scalar.return_value = Mock(spec=DBAddress)
        self.db.execute.return_value = mock_result

        with patch("services.address_service.AddressInDB") as mock_address_schema:
            mock_address_schema.model_validate.return_value = expected_address

            response = await self.service.get_address_by_id(mock_address_id, mock_is_active)

        assert response == expected_address

    @pytest.mark.asyncio
    async def test_get_address_by_id_failed_address_not_found(self):
        mock_address_id = 999

        mock_result = Mock()
        mock_result.scalar.return_value = None
        self.db.execute.return_value = mock_result

        with pytest.raises(ValueError, match=f"Address not found with id: {mock_address_id}"):
            await self.service.get_address_by_id(mock_address_id)

    @pytest.mark.asyncio
    async def test_get_address_by_id_failed_sqlalchemy_error(self):
        mock_address_id = 1

        self.db.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            await self.service.get_address_by_id(mock_address_id)

    @pytest.mark.asyncio
    async def test_get_address_by_id_failed_unknown_error(self):
        mock_address_id = 1

        self.db.execute.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            await self.service.get_address_by_id(mock_address_id)

    @pytest.mark.asyncio
    async def test_get_address_id_success(self):
        mock_address = "0xAddress"
        expected_result = 1

        mock_result = Mock()
        mock_result.scalar.return_value = expected_result
        self.db.execute.return_value = mock_result

        response = await self.service.get_address_id(mock_address)

        assert response == expected_result

    @pytest.mark.asyncio
    async def test_get_address_id_success_with_is_active_filter(self):
        mock_address = "0xAddress"
        mock_is_active = True
        expected_id = 1

        mock_result = Mock()
        mock_result.scalar.return_value = expected_id
        self.db.execute.return_value = mock_result

        response = await self.service.get_address_id(mock_address, mock_is_active)

        assert response == expected_id

    @pytest.mark.asyncio
    async def test_get_address_id_failed_address_id_not_found(self):
        mock_address = "0x99999"

        mock_result = Mock()
        mock_result.scalar.return_value = None
        self.db.execute.return_value = mock_result

        with pytest.raises(ValueError, match=f"Address id not found for: {mock_address}"):
            await self.service.get_address_id(mock_address)

    @pytest.mark.asyncio
    async def test_get_address_id_failed_sqlalchemy_error(self):
        mock_address = "0xAddress"

        self.db.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            await self.service.get_address_id(mock_address)

    @pytest.mark.asyncio
    async def test_get_address_id_failed_unknown_error(self):
        mock_address = "0xAddress"

        self.db.execute.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            await self.service.get_address_id(mock_address)

    @pytest.mark.asyncio
    async def test_get_decrypted_pk_success(self):
        mock_address = "0xAddress"
        mock_encrypted_pk = "encrypted_pk"
        expected_decrypted_pk = "decrypted_pk"

        mock_result = Mock()
        mock_result.scalar.return_value = mock_encrypted_pk
        self.db.execute.return_value = mock_result

        self.mock_security_manager.decrypt_private_key.return_value = expected_decrypted_pk

        response = await self.service.get_decrypted_private_key(mock_address)

        assert response == expected_decrypted_pk

    @pytest.mark.asyncio
    async def test_get_decrypted_pk_success_with_is_active_filter(self):
        mock_address = "0xAddress"
        mock_is_active = True
        mock_encrypted_pk = "encrypted_pk"
        expected_decrypted_pk = "decrypted_pk"

        mock_result = Mock()
        mock_result.scalar.return_value = mock_encrypted_pk
        self.db.execute.return_value = mock_result

        self.mock_security_manager.decrypt_private_key.return_value = expected_decrypted_pk

        response = await self.service.get_decrypted_private_key(mock_address, mock_is_active)

        assert response == expected_decrypted_pk

    @pytest.mark.asyncio
    async def test_get_decrypted_pk_failed_pk_not_found(self):
        mock_address = "0x99999"

        mock_result = Mock()
        mock_result.scalar.return_value = None
        self.db.execute.return_value = mock_result

        with pytest.raises(ValueError, match=f"Private key not found for address: {mock_address}"):
            await self.service.get_decrypted_private_key(mock_address)

    @pytest.mark.asyncio
    async def test_get_decrypted_pk_failed_to_decrypt_pk(self):
        mock_address = "0xAddress"
        mock_encrypted_pk = "encrypted_pk"

        mock_result = Mock()
        mock_result.scalar.return_value = mock_encrypted_pk
        self.db.execute.return_value = mock_result

        self.mock_security_manager.decrypt_private_key.side_effect = Exception("Failed to decrypt private key")

        with pytest.raises(Exception, match="Failed to decrypt private key"):
            await self.service.get_decrypted_private_key(mock_address)

    @pytest.mark.asyncio
    async def test_get_decrypted_pk_failed_sqlalchemy_error(self):
        mock_address = "0xAddress"

        self.db.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            await self.service.get_decrypted_private_key(mock_address)

    @pytest.mark.asyncio
    async def test_get_addresses_ids_batch_success(self):
        mock_addresses = [
            "0xAddress1",
            "0xAddress2",
        ]
        expected_result = {
            "0xAddress1": 1,
            "0xAddress2": 2,
        }
        mock_address_1 = Mock()
        mock_address_1.address = "0xAddress1"
        mock_address_1.id = 1

        mock_address_2 = Mock()
        mock_address_2.address = "0xAddress2"
        mock_address_2.id = 2

        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_address_1, mock_address_2]
        self.db.execute.return_value = mock_result

        response = await self.service.get_addresses_ids_batch(mock_addresses)

        assert response == expected_result

    @pytest.mark.asyncio
    async def test_get_addresses_ids_batch_failed_addresses_not_found(self):
        mock_addresses = [
            "0xAddress1",
            "0xAddress2",
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = []
        self.db.execute.return_value = mock_result

        response = await self.service.get_addresses_ids_batch(mock_addresses)

        assert response == {}

    @pytest.mark.asyncio
    async def test_get_addresses_ids_batch_failed_sqlalchemy_error(self):
        mock_addresses = [
            "0xAddress1",
            "0xAddress2",
        ]

        self.db.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            await self.service.get_addresses_ids_batch(mock_addresses)

    @pytest.mark.asyncio
    async def test_get_addresses_ids_batch_failed_unknown_error(self):
        mock_addresses = [
            "0xAddress1",
            "0xAddress2",
        ]

        self.db.execute.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            await self.service.get_addresses_ids_batch(mock_addresses)