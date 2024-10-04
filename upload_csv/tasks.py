from celery import shared_task
from .trade_matcher import TradeIdMatcher, TradeMatcherProcessor
import logging

logger = logging.getLogger(__name__) 


@shared_task
def process_trade_ids_in_background(owner_id):
    logger.debug(f"Starting background processing for owner: {owner_id}")
    processor = TradeIdMatcher(owner=owner_id)
    asset_ids = processor.check_trade_ids()
    logger.debug(f"Completed processing trade IDs: {asset_ids}")

@shared_task
def process_asset_in_background(owner_id, asset_name):
    logger.debug(f"Processing asset: {asset_name} for owner: {owner_id}")
    try:
        processor = TradeMatcherProcessor(owner=owner_id)
        processor.process_assets(asset_name)
        logger.debug(f"Completed processing asset: {asset_name}")
    except Exception as e:
        logger.error(f"Error processing asset {asset_name}: {e}")