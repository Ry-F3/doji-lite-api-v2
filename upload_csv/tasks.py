from celery import shared_task
from django.contrib.auth.models import User
from .trade_matcher import TradeIdMatcher, TradeMatcherProcessor
from .models import FileName, TradeUploadBlofin
from django.db import transaction
from celery.exceptions import SoftTimeLimitExceeded
import time
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5)
def process_trade_ids_in_background(self, owner_id):
    try:
        logger.debug(f"Starting background processing for owner: {owner_id}")
        processor = TradeIdMatcher(owner=owner_id)

        # Fetch unprocessed trades only
        with transaction.atomic():
            asset_ids = processor.check_trade_ids(chunk_size=100)
            if not asset_ids:
                logger.info(f"No more trades to process for owner: {owner_id}")
                return "All trades processed"  # Exit task when no unprocessed trades remain
            logger.debug(f"Completed processing trade IDs: {asset_ids}")

    except Exception as e:
        logger.error(f"Error in processing trade IDs for owner {owner_id}: {str(e)}")
        raise self.retry(exc=e, countdown=5)  # Retry with a delay


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
                return True  # Stop processing when all trades are done

    except Exception as e:
        logger.error(f"Error processing asset {asset_name}: {e}")
        raise self.retry(exc=e, countdown=5)  # Retry with delay

@shared_task(bind=True, soft_time_limit=90, time_limit=120)
def process_csv_file_async(self, owner_id, file_name_entry_id, csv_content, exchange):
    try:
        owner = User.objects.get(id=owner_id)
        file_name_entry = FileName.objects.get(id=file_name_entry_id)

        logger.debug(f"Starting to process CSV for user: {owner.username}")

        # Reset all trades' is_processed flag when a new file is uploaded
        TradeUploadBlofin.objects.filter(owner=owner).update(is_processed=False)

        # Fetch asset names in chunks to reduce memory usage
        asset_names = TradeUploadBlofin.objects.filter(owner=owner).values_list('underlying_asset', flat=True)

        for asset_name in asset_names:
            time.sleep(1)  # Be cautious with sleep; it can waste time and resources.
            # Process trade IDs for each asset with chunking
            process_trade_ids_in_background.delay(owner.id)
            # Process trades for each asset with chunking
            process_asset_in_background.delay(owner.id, asset_name)
            logger.debug(f"Triggered background task for asset processing: {asset_name}")

        # Save the file_name_entry after processing
        file_name_entry.save()

    except SoftTimeLimitExceeded:
        logger.warning(f"Soft time limit exceeded for task: {self.request.id}. Performing cleanup.")
    except User.DoesNotExist:
        logger.error(f"User with ID {owner_id} does not exist.")
    except FileName.DoesNotExist:
        logger.error(f"FileName with ID {file_name_entry_id} does not exist.")
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")

