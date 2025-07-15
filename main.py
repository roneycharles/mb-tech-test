import logging
import uvicorn

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from api.routes import address, withdraw, deposit
from core.config import settings
from core.database import init_db, async_session_context
from core.logging import config_logging
from core.security import get_security_manager
from jobs.withdraw_jobs import setup_withdraw_jobs
from services.withdraw_service import WithdrawService

load_dotenv()
config_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting application...")

    await init_db()
    logger.info("Database started")

    async with async_session_context() as db_session:
        withdraw_service = WithdrawService(db_session)

        withdraw_jobs, scheduler = await setup_withdraw_jobs(db=db_session, withdraw_service=withdraw_service)
        _app.state.withdraw_jobs = withdraw_jobs
        _app.state.scheduler = scheduler

        logger.info("Withdraw jobs started successfully")
    yield
    logger.info("Shutting down application")

    if hasattr(_app.state, 'withdraw_jobs') and _app.state.withdraw_jobs:
        _app.state.withdraw_jobs.stop()
        logger.info("Withdraw jobs stopped")

    if hasattr(_app.state, 'scheduler') and _app.state.scheduler:
        if _app.state.scheduler.running:
            _app.state.scheduler.shutdown()
        logger.info("Scheduler stopped")

app = FastAPI(
    title="Exchange Backend API",
    description="A robust API for querying and creating blockchain transactions, designed for "
                "seamless integration with exchange backend. Powers secure and efficient crypto operations.",
    version="1.0.0",
    contact={
        "name": "Roney Charles",
        "email": "mmn.charles@gmail.com",
        "linkedIn": "https://www.linkedin.com/in/roneycharles/"
    },
    lifespan=lifespan,
)

app.include_router(address.router, prefix="/api/v1/addresses", tags=["addresses"])
# app.include_router(transaction.router, prefix="/v1/transactions", tags=["transactions"])
app.include_router(withdraw.router, prefix="/api/v1/withdrawals", tags=["withdrawals"])
app.include_router(deposit.router, prefix="/api/v1/deposits", tags=["deposits"])

if __name__ == "__main__":
    logger.info(f"Starting server on {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)