import csv
import gc
from celery import shared_task
from django.contrib.auth.models import User
from .trade_matcher import TradeIdMatcher, TradeMatcherProcessor
from .models import FileName
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5, soft_time_limit=300)
def process_trade_ids_in_background(self, owner_id):
    try:
        logger.debug(f"Starting background processing for owner: {owner_id}")
        processor = TradeIdMatcher(owner=owner_id)

        with transaction.atomic():
            asset_ids = processor.check_trade_ids()
            logger.debug(f"Completed processing trade IDs: {asset_ids}")

    finally:
        # Release the processor object to free memory
        del processor

@shared_task(bind=True, max_retries=5, soft_time_limit=300)
def process_asset_in_background(self, owner_id, asset_name):
    try:
        logger.debug(f"Processing asset: {asset_name} for owner: {owner_id}")
        processor = TradeMatcherProcessor(owner=owner_id)

        with transaction.atomic():
            remaining_trades = processor.process_assets(asset_name)
            logger.debug(f"Remaining trades for asset {asset_name}: {remaining_trades}")

    except Exception as e:
        logger.error(f"Error processing asset {asset_name}: {e}")
        raise self.retry(exc=e, countdown=5)

@shared_task
def process_csv_file_async(owner_id, file_name_entry_id, csv_file_path, exchange):
    try:
        owner = User.objects.get(id=owner_id)
        file_name_entry = FileName.objects.get(id=file_name_entry_id)
        logger.debug(f"Starting to process CSV for user: {owner.username}")

        # Open the CSV file directly, avoiding loading into memory
        with open(csv_file_path, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)

            for row in csv_reader:
                if not row:  # Skip empty rows
                    continue
                asset_name = row[0]  # Assuming asset name is in the first column
                process_trade_ids_in_background.delay(owner.id)  # Process trade IDs for each asset
                process_asset_in_background.delay(owner.id, asset_name)  # Process trades for each asset
                logger.debug(f"Triggered background task for asset processing: {asset_name}")

    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
    finally:
        # Clear memory if needed, though not often necessary
        gc.collect()
