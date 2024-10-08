from celery import shared_task, group, chord
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
            asset_ids = processor.check_trade_ids(chunk_size=100)  # Example of processing in chunks
            logger.debug(f"Completed processing trade IDs: {asset_ids}")

    except Exception as e:
        logger.error(f"Error in processing trade IDs for owner {owner_id}: {str(e)}")
        raise self.retry(exc=e, countdown=5)  # Retry with a delay

@shared_task(bind=True, max_retries=5)
def process_asset_in_background(self, owner_id, asset_name):
    try:
        logger.debug(f"Processing asset: {asset_name} for owner: {owner_id}")
        processor = TradeMatcherProcessor(owner=owner_id)

        with transaction.atomic():
            remaining_trades = processor.process_assets(asset_name, chunk_size=100)
            if remaining_trades == 0:
                logger.debug(f"All trades processed for asset: {asset_name}")
                return True
            else:
                logger.debug(f"Remaining trades for asset {asset_name}: {remaining_trades}")
                return False  
    except Exception as e:
        logger.error(f"Error processing asset {asset_name}: {e}")
        raise self.retry(exc=e, countdown=5)  # Retry with delay


@shared_task(bind=True, soft_time_limit=90, time_limit=120)
def process_csv_file_async(self, owner_id, file_name_entry_id, csv_content, exchange):
    try:
        owner = User.objects.get(id=owner_id)
        file_name_entry, created = FileName.objects.get_or_create(id=file_name_entry_id)

        logger.debug(f"Starting to process CSV for user: {owner.username}")

        # Set the processing flag to True at the start
        file_name_entry.processing = True
        file_name_entry.save()
        logger.info(f"File {file_name_entry_id} marked as processing.")

        # Fetch unique asset names
        asset_names = TradeUploadBlofin.objects.filter(owner=owner).values_list('underlying_asset', flat=True).distinct()

        if not asset_names:
            logger.warning(f"No assets found for owner: {owner_id}. Skipping processing.")
            return

        # Optionally, process trade IDs once before processing assets
        process_trade_ids_in_background.delay(owner.id)

        # Collect tasks for each asset
        asset_tasks = []
        for asset_name in asset_names:
            if asset_name:
                logger.debug(f"Adding task for asset: {asset_name} for owner: {owner_id}")
                asset_tasks.append(process_asset_in_background.s(owner.id, asset_name))
            else:
                logger.warning(f"Encountered empty asset name for owner: {owner_id}. Skipping.")

        # Create a chord: group of tasks with a callback
        task_group = group(asset_tasks)
        callback = finalize_file_processing.s(file_name_entry_id)
        chord(task_group)(callback)

    except SoftTimeLimitExceeded:
        logger.warning(f"Soft time limit exceeded for task: {self.request.id}. Performing cleanup.")
    except User.DoesNotExist:
        logger.error(f"User with ID {owner_id} does not exist.")
    except FileName.DoesNotExist:
        logger.error(f"FileName with ID {file_name_entry_id} does not exist.")
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")

@shared_task(bind=True)
def finalize_file_processing(self, results, file_name_entry_id):
    try:
        file_name_entry = FileName.objects.get(id=file_name_entry_id)
        file_name_entry.processing = False
        file_name_entry.save()
        logger.info(f"File {file_name_entry_id} processing completed.")
    except FileName.DoesNotExist:
        logger.error(f"FileName with ID {file_name_entry_id} does not exist.")
    except Exception as e:
        logger.error(f"Error finalizing file processing: {str(e)}")
