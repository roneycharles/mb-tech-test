import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from hexbytes import HexBytes
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import TransactionNotFound, ContractLogicError, Web3Exception
from web3.types import ChecksumAddress

from constants.blockchain import ERC20_BASIC_ABI
from core.config import settings
from schemas.blockchain import TransferInfo
from services.token_service import TokenService

logger = logging.getLogger(__name__)

class BlockchainService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.token_service = TokenService(db)

        self.w3 = Web3(Web3.HTTPProvider(settings.RPC_URL))
        if not self.w3.is_connected():
            logger.error("Failed to connect to RPC node at %s", settings.RPC_URL)
            raise ConnectionError(f"Cannot connect to RPC node at {settings.RPC_URL}")

        logger.debug("Connected to RPC node at %s", settings.RPC_URL)

        self.w3 = Web3(Web3.HTTPProvider(settings.RPC_URL))
        self.chain_id = settings.CHAIN_ID

        self.erc20_transfer_signature_hash = Web3.keccak(text="Transfer(address,address,uint256)").to_0x_hex()
        self.erc20_contract_for_events = self.w3.eth.contract(abi=ERC20_BASIC_ABI)

    def _create_token_contract(self, address: str) -> Optional[Contract]:
        try:
            checksum_address = self._to_checksum_address(address)
            contract = self.w3.eth.contract(address=checksum_address, abi=ERC20_BASIC_ABI)

            try:
                contract.functions.symbol().call()
                logger.debug("Contract loaded successfully for: %s", address)
                return contract
            except ContractLogicError as e:
                logger.error("Contract validation failed for %s: %s", address, e)
                return None
            except Exception as e:
                logger.error("Failed to validate contract for %s: %s", address, e)
                return None

        except ValueError as e:
            logger.error("Invalid address format %s: %s", address, e)
            return None
        except Exception as e:
            logger.error("Failed to create contract for %s: %s", address, e)
            return None

    async def get_transaction_data(self, tx_hash: str) -> Optional[Dict]:
        try:
            tx_hash_hex: HexBytes = HexBytes(tx_hash)
            tx = self.w3.eth.get_transaction(tx_hash_hex)
            receipt = self.w3.eth.get_transaction_receipt(tx_hash_hex)

            return {
                'transaction': tx,
                'receipt': receipt,
                'block_number': receipt['blockNumber'],
                'status': receipt['status'],
            }
        except TransactionNotFound:
            logger.warning("Transaction not found: %s", tx_hash)
            return None
        except ValueError as e:
            logger.error("Invalid transaction hash format %s: %s", tx_hash, e)
            return None
        except Web3Exception as e:
            logger.error("Web3 error getting transaction %s: %s", tx_hash, e)
            return None
        except Exception as e:
            logger.error("Unexpected error getting transaction %s: %s", tx_hash, e)
            return None

    async def get_transaction_transfers(self, tx_data: Dict) -> List[TransferInfo]:
        if not tx_data:
            logger.error("Transaction data is empty")
            return []

        tx = tx_data['transaction']
        receipt = tx_data['receipt']
        transfers: List[TransferInfo] = []

        if tx['value'] > 0:
            try:
                from_address = tx['from']
                to_address = receipt['to']

                token = await self.token_service.get_token_by_symbol("ETH")
                if not token:
                    logger.error("Token not found in database: ETH")
                    return []

                amount = self.from_wei(tx['value'], token.decimals)

                transfers.append(
                    TransferInfo(
                        token_id=token.id,
                        from_address=from_address.lower(),
                        to_address=to_address.lower(),
                        amount=amount,
                    )
                )
            except Exception as e:
                logger.error("Failed to get ETH transfers: %s", e)

        try:
            for log in receipt['logs']:
                try:
                    if log['topics'] and log['topics'][0].to_0x_hex() == self.erc20_transfer_signature_hash:
                        decoded_log = self.erc20_contract_for_events.events.Transfer().process_log(log)

                        from_address = decoded_log['args']['from']
                        to_address = decoded_log['args']['to']
                        amount_wei = decoded_log['args']['value']
                        token_address = log['address']

                        token = await self.token_service.get_token_by_address(address=token_address.lower(), is_active=True)
                        if not token:
                            logger.error("Token not found in database: %s", token_address)
                            continue

                        amount = self.from_wei(amount_wei, token.decimals)

                        transfers.append(
                            TransferInfo(
                                token_id=token.id,
                                from_address=from_address.lower(),
                                to_address=to_address.lower(),
                                amount=amount,
                            )
                        )
                except Exception as e:
                    logger.error("Could not decode log as Transfer event: %s", e)
                    continue

            return transfers
        except Exception as e:
            logger.error("Failed to parse transaction logs: %s", e)
            raise

    async def check_transaction_security(self, tx_data: Dict) -> bool:
        try:
            status = tx_data['status']
            block_number = tx_data['block_number']

            if status != 1:
                logger.warning("Transaction failed on blockchain with status: %s", status)
                return False

            confirmations = await self.get_transaction_confirmations(block_number)
            if not confirmations:
                logger.error("Failed to get confirmations for block number: %s", block_number)
                return False
            elif confirmations < settings.MIN_CONFIRMATIONS:
                logger.warning("Transaction has insufficient confirmations: %d (required: %d)", confirmations, settings.MIN_CONFIRMATIONS)
                return False

            logger.info("Transaction has sufficient confirmations: %s", confirmations)

            return True
        except KeyError as e:
            logger.error("Invalid transaction data, missing field: %s", e)
            return False
        except Exception as e:
            logger.error("Failed to check transaction security: %s", e)
            return False

    async def get_transaction_confirmations(self, tx_block_number: int) -> Optional[int]:
        try:
            current_block = self.w3.eth.block_number
            confirmations = current_block - tx_block_number

            if confirmations < 0:
                logger.error("Current block number %d is older than transaction block %d", current_block, tx_block_number)
                return None

            logger.info("Transaction confirmations: %s", confirmations)

            return confirmations
        except Web3Exception as e:
            logger.error("Web3 error getting block number: %s", e)
            return None
        except Exception as e:
            logger.error("Failed to get transaction confirmations: %s", e)
            return None

    async def build_eth_transaction(self, from_address: str, to_address: str, amount: Decimal) -> Dict:
        try:
            checksum_from_address = self._to_checksum_address(from_address)
            checksum_to_address = self._to_checksum_address(to_address)
            nonce = self.w3.eth.get_transaction_count(checksum_from_address)

            gas_limit = settings.ETH_GAS_LIMIT
            gas_price = self.w3.eth.gas_price
            estimate_gas_cost = (gas_limit * gas_price)

            amount_wei = self.to_wei(amount, 18)

            balance_needed = amount_wei + estimate_gas_cost

            if not await self._is_sufficient_eth_balance(address=checksum_from_address, amount=balance_needed):
                logger.error("Insufficient ETH balance for address: %s", checksum_from_address)
                raise ValueError(f"Insufficient ETH balance for address: {checksum_from_address}")

            return {
                "nonce": nonce,
                "to": checksum_to_address,
                "value": amount_wei,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": self.chain_id,
            }
        except ValueError:
            raise
        except Web3Exception as e:
            logger.error("Web3 error building ETH transaction: %s", e)
            raise
        except Exception as e:
            logger.error("Failed to build ETH transaction: %s", e)
            raise

    async def build_token_transaction(self, from_address: str, to_address: str, amount: Decimal, token_address: str, decimals: int) -> Dict:
        try:
            checksum_from_address = self._to_checksum_address(from_address)
            checksum_to_address = self._to_checksum_address(to_address)

            token_contract = self._create_token_contract(token_address)
            if not token_contract:
                logger.error("Failed to create contract for token: %s", token_address)
                raise ValueError(f"Failed to create contract for token: {token_address}")

            amount_wei = self.to_wei(amount, decimals)

            if not await self._is_sufficient_token_balance(contract=token_contract, address=checksum_from_address, amount=amount_wei):
                logger.error("Insufficient token balance for address: %s", checksum_from_address)
                raise ValueError(f"Insufficient token balance for token: {checksum_from_address}")

            nonce = self.w3.eth.get_transaction_count(checksum_from_address)

            gas_price, gas_limit = await self.estimate_erc20_gas_params(
                contract=token_contract,
                from_address=checksum_from_address,
                to_address=checksum_to_address,
                amount=amount_wei,
            )

            estimate_gas_cost = (gas_price * gas_limit)

            if not await self._is_sufficient_eth_balance(address=checksum_from_address, amount=estimate_gas_cost):
                logger.error("Insufficient ETH balance to pay gas cost: %s", estimate_gas_cost)
                raise ValueError(f"Insufficient eth balance to pay gas cost: {estimate_gas_cost}")

            tx_data = token_contract.functions.transfer(
                checksum_to_address,
                amount_wei
            ).build_transaction({
                'nonce': nonce,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'chainId': self.chain_id,
            })

            return tx_data
        except ValueError:
            raise
        except Web3Exception as e:
            logger.error("Web3 error building token transaction: %s", e)
            raise
        except Exception as e:
            logger.error("Failed to build token transaction: %s", e)
            raise

    @staticmethod
    def to_wei(amount: Decimal, decimals: int) -> int:
        return int(Decimal(str(amount)) * (Decimal(10) ** decimals))

    @staticmethod
    def from_wei(amount: int, decimals: int) -> Decimal:
        return Decimal(amount) / (Decimal(10) ** decimals)

    def _to_checksum_address(self, address: str) -> ChecksumAddress:
        try:
            address = address.strip()

            if not address.startswith("0x") or len(address) != 42:
                logger.error("Invalid address format: %s", address)
                raise ValueError(f"Invalid address format: {address}")

            return self.w3.to_checksum_address(address)
        except Exception as e:
            raise ValueError(f"Failed to convert address to checksum_address: {address}: {str(e)}")

    @staticmethod
    async def _is_sufficient_token_balance(contract: Contract, address: ChecksumAddress, amount: int) -> bool:
        try:
            balance = contract.functions.balanceOf(address).call()
            if balance < amount:
                logger.error("Insufficient token balance. Required: %d, Available: %d", amount, balance)
                return False

            return True
        except ContractLogicError as e:
            logger.error("Contract logic error checking token balance: %s", e)
            return False
        except Web3Exception as e:
            logger.error("Web3 error checking token balance: %s", e)
            return False
        except Exception as e:
            logger.error("Failed to check token balance: %s", e)
            return False

    async def estimate_erc20_gas_params(self, contract: Contract, from_address: ChecksumAddress, to_address: ChecksumAddress, amount: int) -> Tuple[int, int]:
        try:
            estimated_gas = contract.functions.transfer(to_address, amount).estimate_gas({'from': from_address})
            gas_limit = int(estimated_gas * settings.GAS_LIMIT_MULTIPLIER)

            if gas_limit > settings.ERC20_GAS_LIMIT:
                logger.warning("Estimated gas limit %s exceeded max ERC20 limit %s", gas_limit, settings.MAX_GAS_LIMIT)
                gas_limit = settings.ERC20_GAS_LIMIT

            network_gas_price = self.w3.eth.gas_price
            gas_price = int(network_gas_price * settings.GAS_PRICE_MULTIPLIER)

            return gas_price, gas_limit
        except ContractLogicError as e:
            logger.error("Contract logic error estimating gas: %s", e)
            default_gas_price = int(settings.GAS_PRICE * settings.GAS_PRICE_MULTIPLIER)
            default_gas_limit = settings.ERC20_GAS_LIMIT
            return default_gas_price, default_gas_limit
        except Web3Exception as e:
            logger.error("Web3 error estimating ERC20 transfer gas: %s", e)
            default_gas_price = int(settings.GAS_PRICE * settings.GAS_PRICE_MULTIPLIER)
            default_gas_limit = settings.ERC20_GAS_LIMIT
            return default_gas_price, default_gas_limit
        except Exception as e:
            logger.error("Failed to estimate ERC20 transfer gas: %s", e)
            default_gas_price = int(settings.GAS_PRICE * settings.GAS_PRICE_MULTIPLIER)
            default_gas_limit = settings.ERC20_GAS_LIMIT
            return default_gas_price, default_gas_limit

    async def send_transaction(self, tx_params: Dict, private_key: str) -> str:
        try:
            signed_tx = self.w3.eth.account.sign_transaction(tx_params, private_key=private_key)
            if not signed_tx:
                logger.error("Failed to sign transaction")
                raise ValueError("Failed to sign transaction")

            tx_hash_bytes = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = tx_hash_bytes.hex()
            if not tx_hash.startswith('0x'):
                tx_hash = '0x' + tx_hash

            logger.info("Transaction sent: %s", tx_hash)
            return tx_hash
        except ValueError:
            raise
        except Web3Exception as e:
            logger.error("Web3 error sending transaction: %s", e)
            raise
        except Exception as e:
            logger.error("Failed to send transaction: %s", e)
            raise

    async def _is_sufficient_eth_balance(self, address: ChecksumAddress, amount: int) -> bool:
        try:
            balance = self.w3.eth.get_balance(address)
            if balance < amount:
                logger.error("Insufficient ETH balance. Required: %d, Available: %d", amount, balance)
                return False

            return True
        except Web3Exception as e:
            logger.error("Web3 error checking ETH balance: %s", e)
            return False
        except Exception as e:
            logger.error("Failed to check ETH balance: %s", e)
            return False

    def calculate_gas_cost(self, tx_data: Dict) -> Decimal:
        try:
            receipt = tx_data['receipt']
            transaction = tx_data['transaction']

            gas_used = receipt.get('gasUsed', 0)
            gas_price = transaction.get('gasPrice', 0)

            if gas_used == 0 or gas_price == 0:
                logger.error("Gas calculation with zero values: gas_used=%d, gas_price=%d", gas_used, gas_price)
                return Decimal(0)

            gas_cost_wei = gas_used * gas_price
            gas_cost_eth = self.from_wei(gas_cost_wei, 18)

            logger.info("Gas cost calculated: %s ETH (gas_used=%s, gas_price=%s)", gas_cost_eth, gas_used, gas_price)
            return gas_cost_eth

        except KeyError as e:
            logger.error("Missing field in transaction data for gas calculation: %s", e)
            return Decimal(0)
        except Exception as e:
            logger.error("Failed to calculate gas cost: %s", e)
            return Decimal(0)