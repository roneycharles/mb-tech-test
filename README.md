# Exchange Backend API

A robust API for querying and creating blockchain transactions, 
designed for seamless integration with exchange backend. 
Powers secure and efficient crypto operations.

## Services Overview
### Addresses Service

- **Secure Key Generation**: Creates secure Ethereum addresses using industry-standard secp256k1 cryptography (eth_account)
- **High Entropy**: Uses high entropy to generate cryptographically secure addresses
- **Enhanced Security**: Encrypts private keys before database storage and decrypts only during transaction execution
- **Address Management**: Provides comprehensive listing and management of all created addresses
- **Ownership Verification**: Implements address ownership verification for enhanced security

### Blockchain Service

- **Transaction Monitoring**: Queries and tracks transactions on the Ethereum blockchain with real-time status monitoring
- **Safety Validation**: Validates transaction security by checking status and confirmation
- **Multi-Asset Support**: Creates transfer transactions for both Ethereum and ERC-20 tokens
- **Gas Optimization**: Implements intelligent gas price limits and safety margins to ensure successful transaction execution

### Deposits Service

- **Secure Processing**: Creates database transactions with strict validation of destination addresses
- **Token Control**: Restricts transactions to registered tokens only, preventing unauthorized asset handling
- **Address Validation**: Ensures all destination addresses are valid and exist in the database
- **Transaction History**: Maintains complete records of all processed deposits
- **Complete Tracking**: Provides full visibility into all deposits transactions

### Withdrawals Service

- **Comprehensive Validation**: Creates database transactions with strict validation of source addresses and registered tokens
- **Automated Processing**: Background scheduler automatically processes pending withdrawals and submits to blockchain
- **State Management**: Maintains proper nonce control for address transactions to prevent conflicts
- **Status Synchronization**: Secondary background process monitors blockchain status and updates withdrawal records accordingly
- **Complete Tracking**: Provides full visibility into all withdrawal transactions and their current status

## Architecture
- **API Layer**: FastAPI endpoints for REST API
- **Service Layer**: Business logic and transaction processing
- **Data Layer**: SQLAlchemy models and database operations
- **Blockchain Layer**: Web3.py integration for Sepolia Testnet interaction
- **Scheduler Layer**: Cronjob for automated transaction processing and status confirmation

## Tech Stack
- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Blockchain**: Web3.py for Sepolia Testnet interaction
- **Containerization**: Docker and Docker Compose
- **Task Scheduling**: APScheduler (AsyncIOScheduler) for automated background tasks

## Requirements

- **Python**: 3.11+
- **Docker**: For containerized deployment
- **Docker Compose**: For orchestrating containers
- **PostgreSQL**: Database (can be run via Docker)

## Configuration
The project includes a `.env.example` file 
with all required environment variables. Simply rename it to `.env`

## Usage

### Install Requirements
```bash
# Create .venv path and install all requirements
make install
```

### Activate Virtual Environment
```bash
# Activate Virtual Environment
source .venv/bin/activate
```

### Start Services
```bash
# Start docker services(database and application)
make start
```

### Run Seeds
Note: Make sure the application is running first to create the database tables.
```bash
# Populate database with initial data
make seed
```

### API Endpoints

### Addresses
- `POST /api/v1/addresses` - Create new addresses
- `GET /api/v1/addresses` - List generated addresses

### Deposits
- `POST /api/v1/deposits` - Create new deposit
- `GET /api/v1/deposits` - List computed deposits

### Withdrawals
- `POST /api/v1/withdrawals` - Create new withdraw
- `GET /api/v1/withdrawals` - List computed withdrawals

### Example Usage
```bash
# POST /api/v1/addresses - Create new addresses
curl -X 'POST' \
  'http://0.0.0.0:3000/api/v1/addresses/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "quantity": 10
}'

# GET /api/v1/addresses - List generated addresses
curl -X 'GET' \
  'http://0.0.0.0:3000/api/v1/addresses/?page_size=50&page=1' \
  -H 'accept: application/json'

# POST /api/v1/deposits - Create new deposit
curl -X 'POST' \
  'http://0.0.0.0:3000/api/v1/deposits/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "tx_hash": "0x035fbf8daced9a8ed4194e8ddb190309a3dba7e1cd83c1f0efb24bee73645877"
}'

# GET /api/v1/deposits - List computed deposits
curl -X 'GET' \
  'http://0.0.0.0:3000/api/v1/deposits/?page_size=50&page=1' \
  -H 'accept: application/json'

# POST /api/v1/withdrawals - Create new withdraw
curl -X 'POST' \
  'http://0.0.0.0:3000/api/v1/withdrawals/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "from_address": "0xAA4433433ef0bd4bAfd336ce65a5C4Fc38C4FB82",
  "to_address": "0xCbB658D8e3aB33956DCa53a13fD9d47A00159d39",
  "symbol": "USDC",
  "amount": 10
}'

# GET /api/v1/withdrawals - List computed withdrawals
curl -X 'GET' \
  'http://0.0.0.0:3000/api/v1/withdrawals/?page=1&page_size=50' \
  -H 'accept: application/json'
```
## Links
### [Ethereum Sepolia Faucet](https://sepolia-faucet.pk910.de/#/)
### [Sepolia Testnet Explorer](https://sepolia.etherscan.io/)
### [Swap: ETH/USDC](https://app.uniswap.org/explore/tokens/ethereum_sepolia/0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238?inputCurrency=NATIVE&outputCurrency=0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238)