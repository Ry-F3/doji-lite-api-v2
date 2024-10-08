from celery import shared_task
from django.contrib.auth.models import User
from .trade_matcher import TradeIdMatcher, TradeMatcherProcessor
from .models import FileName, TradeUploadBlofin
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5)
def process_trade_ids_in_background(self, owner_id):
    try:
        logger.debug(f"Starting background processing for owner: {owner_id}")
        processor = TradeIdMatcher(owner=owner_id)

        # Fetch unprocessed trades only
        with transaction.atomic():
            # Check for cancellation before processing
            file_name_entry = FileName.objects.get(owner_id=owner_id)  # Assuming you can fetch it this way
            if file_name_entry.cancel_processing:
                logger.info("Cancellation requested. Exiting process_trade_ids_in_background.")
                return

            asset_ids = processor.check_trade_ids()
            logger.debug(f"Completed processing trade IDs: {asset_ids}")
    finally:
        connection.close()  # Explicitly close the database connection

@shared_task(bind=True, max_retries=5)
def process_asset_in_background(self, owner_id, asset_name):
    try:
        logger.debug(f"Processing asset: {asset_name} for owner: {owner_id}")
        processor = TradeMatcherProcessor(owner=owner_id)

        # Process unprocessed trades for the asset
        with transaction.atomic():
            file_name_entry = FileName.objects.get(owner_id=owner_id)  # Fetch it again to check for cancellation
            if file_name_entry.cancel_processing:
                logger.info("Cancellation requested. Exiting process_asset_in_background.")
                return

            remaining_trades = processor.process_assets(asset_name)
            if remaining_trades == 0:
                logger.debug(f"All trades processed for asset: {asset_name}")
                return True  # Stop processing as all trades are done
            else:
                logger.debug(f"Remaining trades for asset {asset_name}: {remaining_trades}")

    except Exception as e:
        logger.error(f"Error processing asset {asset_name}: {e}")
        raise self.retry(exc=e, countdown=5)  # Retry with delay

@shared_task
def process_csv_file_async(owner_id, file_name_entry_id, csv_content, exchange):
    try:
        owner = User.objects.get(id=owner_id)
        file_name_entry = FileName.objects.get(id=file_name_entry_id)
        logger.debug(f"Starting to process CSV for user: {owner.username}")

        # Set processing flag to True
        file_name_entry.processing = True
        file_name_entry.save()

        # Fetch asset names to be processed
        asset_names = TradeUploadBlofin.objects.filter(owner=owner).values_list('underlying_asset', flat=True)
        logger.debug(f"Retrieved asset names: {list(asset_names)}")

        # Loop through each asset and trigger background tasks
        for asset_name in asset_names:
            process_trade_ids_in_background.delay(owner.id)  # Process trade IDs for each asset
            process_asset_in_background.delay(owner.id, asset_name)  # Process trades for each asset
            logger.debug(f"Triggered background task for asset processing: {asset_name}")

            # Check for cancellation after processing each asset
            if file_name_entry.cancel_processing:
                logger.info("Processing cancelled. Exiting.")
                return  # Exit the task
                
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
    finally:
        # Reset processing flag
        file_name_entry.processing = False
        file_name_entry.cancel_processing = False  # Reset cancel flag
        file_name_entry.save()
