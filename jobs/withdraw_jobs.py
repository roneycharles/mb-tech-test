import logging
from typing import List, Dict, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from constants.withdraw import WithdrawStatus
from schemas.withdraw import WithdrawInDB
from services.withdraw_service import WithdrawService

logger = logging.getLogger(__name__)

class WithdrawJobs:

    def __init__(self, db: AsyncSession, withdraw_service: WithdrawService, scheduler: AsyncIOScheduler):
        self.db = db
        self.withdraw_service = withdraw_service
        self.scheduler = scheduler

    def setup_jobs(self):
        self.scheduler.add_job(
            self.update_withdraw_job,
            trigger="interval",
            seconds=30,
            id="update_withdraw",
            name="Update withdraw status",
            max_instances=1,
            replace_existing=True,
            coalesce=True,
        )

        self.scheduler.add_job(
            self.send_withdraw_job,
            trigger="interval",
            seconds=30,
            id="send_withdraw",
            name="Send pending withdraw",
            max_instances=1,
            replace_existing=True,
            coalesce=True,
        )

    async def send_withdraw_job(self):
        logger.info("Starting send withdraw job")

        try:
            pending_withdrawals = await self.withdraw_service.get_withdrawals_by_status(WithdrawStatus.PENDING)
            if not pending_withdrawals:
                logger.info("No pending withdrawals found")
                return

            withdrawals_by_address = self._group_withdrawals_by_address(pending_withdrawals)
            processed_count = 0
            failed_count = 0

            for address_id, withdrawals in withdrawals_by_address.items():
                try:
                    if not await self.withdraw_service.can_process_withdraw(address_id):
                        failed_count += 1
                        logger.info("Cannot processed withdraw for address id: %d", address_id)
                        continue

                    old_withdraw = withdrawals[0]

                    if await self.withdraw_service.process_withdraw(old_withdraw):
                        processed_count += 1
                        logger.info("Successfully processed withdraw with id: %d", old_withdraw.id)
                    else:
                        failed_count += 1
                        logger.error("Failed to process withdraw with id: %d", old_withdraw.id)

                except Exception as e:
                    failed_count += 1
                    logger.error("Failed to process withdraw with id %d: %s: ", address_id, e)

            logger.info("Send withdraw job completed: Processed: %d - Failed: %d", processed_count, failed_count)
        except Exception as e:
            logger.error("Send withdraw job failed: %s", e)

    @staticmethod
    def _group_withdrawals_by_address(withdrawals: List[WithdrawInDB]) -> Dict[int, List[WithdrawInDB]]:
        group_by_address = {}

        for withdraw in withdrawals:
            if withdraw.address_id not in group_by_address:
                group_by_address[withdraw.address_id] = []

            group_by_address[withdraw.address_id].append(withdraw)

        return group_by_address

    async def update_withdraw_job(self):
        logger.info("Starting update withdraw job")

        try:
            in_progress_withdrawals = await self.withdraw_service.get_withdrawals_by_status(WithdrawStatus.IN_PROGRESS)
            if not in_progress_withdrawals:
                logger.info("No in-progress withdrawals found")
                return

            updated_count = 0
            failed_count = 0

            for withdraw in in_progress_withdrawals:
                try:
                    if await self.withdraw_service.update_withdraw_status(withdraw):
                        updated_count += 1
                        logger.info("Successfully updated withdraw with id: %s", withdraw.id)
                    else:
                        failed_count += 1
                        logger.error("Failed to update withdraw with id: %s", withdraw.id)

                except Exception as e:
                    failed_count += 1
                    logger.error("Failed to update withdraw with id %s: %s", withdraw.id, e)

            logger.info("Update withdraw job completed: Updated: %d - Failed: %d", updated_count, failed_count)
        except Exception as e:
            logger.error("Update withdraw failed: %s", e)

    def start(self):
        try:
            self.setup_jobs()
            logger.info("Withdraw jobs started")
        except Exception as e:
            logger.error("Failed to start withdraw jobs: %s", e)

    def stop(self):
        try:
            if self.scheduler.running:
                self.scheduler.remove_job("send_withdraw")
                self.scheduler.remove_job("update_withdraw")
            logger.info("Withdraw jobs stopped")
        except Exception as e:
            logger.error("Failed to stop withdraw jobs: %s", e)

async def setup_withdraw_jobs(db: AsyncSession, withdraw_service: WithdrawService) -> Tuple[WithdrawJobs, AsyncIOScheduler]:

    try:
        scheduler = AsyncIOScheduler()

        withdraw_jobs = WithdrawJobs(db= db, withdraw_service=withdraw_service ,scheduler=scheduler)
        withdraw_jobs.start()
        scheduler.start()

        return withdraw_jobs, scheduler
    except Exception as e:
        logger.error("Failed to setup withdraw jobs: %s", e)
        raise