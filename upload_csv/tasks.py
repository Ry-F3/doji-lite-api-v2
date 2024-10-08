from celery import shared_task
from django.contrib.auth.models import User
from .trade_matcher import TradeIdMatcher, TradeMatcherProcessor
from .models import FileName, TradeUploadBlofin
from django.db import transaction
import logging
import time

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5)
def process_trade_ids_in_background(self, owner_id):
    try:
        logger.debug(f"Starting background processing for owner: {owner_id}")
        processor = TradeIdMatcher(owner=owner_id)

        # Fetch and process unprocessed trade IDs in chunks
        with transaction.atomic():
            asset_ids = processor.check_trade_ids(chunk_size=100)
            logger.debug(f"Completed processing trade IDs: {asset_ids}")

    except Exception as e:
        logger.error(f"Error in processing trade IDs for owner {owner_id}: {str(e)}")
        self.retry(exc=e, countdown=10)  # Retry after 10 seconds


@shared_task(bind=True, max_retries=5)
def process_asset_in_background(self, owner_id, asset_name):
    try:
        logger.debug(f"Processing asset: {asset_name} for owner: {owner_id}")
        processor = TradeMatcherProcessor(owner=owner_id)

        # Process unprocessed trades for the asset in chunks
        with transaction.atomic():
            remaining_trades = processor.process_assets(asset_name, chunk_size=100)
            if remaining_trades == 0:
                logger.debug(f"All trades processed for asset: {asset_name}")
                return True  # All trades for the asset have been processed

            logger.debug(f"Remaining trades for asset {asset_name}: {remaining_trades}")
            return False

    except Exception as e:
        logger.error(f"Error processing asset {asset_name}: {e}")
        self.retry(exc=e, countdown=10)  # Retry after 10 seconds


@shared_task(bind=True, max_retries=3)
def process_csv_file_async(self, owner_id, file_name_entry_id, csv_content, exchange):
    try:
        # Fetch the user and file name entry
        owner = User.objects.get(id=owner_id)
        file_name_entry = FileName.objects.get(id=file_name_entry_id)

        logger.debug(f"Starting to process CSV for user: {owner.username}, file entry: {file_name_entry}")

        # Get asset names linked to the user from the TradeUploadBlofin model
        asset_names = TradeUploadBlofin.objects.filter(owner=owner).values_list('underlying_asset', flat=True)

        # Loop through each asset and trigger background tasks in chunks
        for asset_name in asset_names:
            time.sleep(1)  # Avoid overwhelming the task queue

            # Trigger background processing for trade IDs
            process_trade_ids_in_background.delay(owner.id)

            # Trigger background processing for asset matching
            process_asset_in_background.delay(owner.id, asset_name)

            logger.debug(f"Background tasks triggered for asset processing: {asset_name}")

        # After successfully processing all assets, save the file entry
        file_name_entry.processed = True  # Mark the file as processed
        file_name_entry.save()

        logger.debug(f"Completed processing CSV file for user: {owner.username}")

    except User.DoesNotExist:
        logger.error(f"User with ID {owner_id} does not exist.")
    except FileName.DoesNotExist:
        logger.error(f"FileName with ID {file_name_entry_id} does not exist.")
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        self.retry(exc=e, countdown=10)  # Retry after 10 seconds if an error occurs
