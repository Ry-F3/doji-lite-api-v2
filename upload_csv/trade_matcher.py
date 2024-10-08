import json
from django.utils import timezone
from django.db import transaction
from .models import TradeUploadBlofin
from decimal import Decimal
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set the desired log level
logger = logging.getLogger(__name__)

class TradeMatcherProcessor:
    def __init__(self, owner):
        self.owner = owner
        self.trades_by_asset = {}

    def process_assets(self, asset_name, chunk_size=None):
        logger.debug(f"Starting asset processing for: {asset_name}")
        self.revert_filled_quantity_values(asset_name)
        self.process_asset_match(asset_name)

    def revert_filled_quantity_values(self, asset_name):
        """Revert all trades' filled_quantity values to their original_filled_quantity before processing."""
        with transaction.atomic():
            trades = TradeUploadBlofin.objects.filter(
                owner=self.owner,
                underlying_asset=asset_name
            )

            if not trades.exists():
                logger.warning(f"No trades found for asset {asset_name}. Skipping revert.")
                return

            for trade in trades:
                original_value = trade.original_filled_quantity
                if original_value is None:
                    logger.warning(f"Trade ID={trade.id} does not have an original_filled_quantity. Skipping revert.")
                    continue

                try:
                    TradeUploadBlofin.objects.filter(id=trade.id).update(
                        filled_quantity=original_value,
                        is_open=False,
                        is_matched=False,
                        is_partially_matched=False,
                    )
                    logger.info(f"Reverted trade ID={trade.id} filled_quantity to {original_value}.")

                except Exception as e:
                    logger.error(f"Failed to revert trade ID={trade.id}. Error: {e}")

    def process_asset_match(self, asset_name):
        logger.debug(f"Processing asset match for: {asset_name}")

        trades = TradeUploadBlofin.objects.filter(
            owner=self.owner,
            underlying_asset=asset_name,
        )

        buys = list(trades.filter(side='Buy').values_list('id', 'filled_quantity'))
        sells = list(trades.filter(side='Sell').values_list('id', 'filled_quantity'))

        logger.debug(f"Buys: {buys}, Sells: {sells}")

        buy_status = [{'id': buy[0], 'value': buy[1], 'is_matched': False, 'is_partially_matched': False, 'is_open': True} for buy in buys]
        sell_status = [{'id': sell[0], 'value': sell[1], 'is_matched': False, 'is_partially_matched': False, 'is_open': True} for sell in sells]

        i = 0  # Pointer for `buys`
        while i < len(buy_status) and sell_status:
            logger.debug(f"Processing Buy ID: {buy_status[i]['id']} with value: {buy_status[i]['value']}")
            logger.debug(f"Current Sell ID: {sell_status[0]['id']} with value: {sell_status[0]['value']}")

            if buy_status[i]['value'] >= sell_status[0]['value']:
                buy_status[i]['value'] -= sell_status[0]['value']
                sell_status[0]['value'] = 0

                sell_status[0]['is_matched'] = True
                sell_status[0]['is_open'] = False
                self.update_trade_status(sell_status)
                logger.info(f"Matched Sell ID: {sell_status[0]['id']} with Buy ID: {buy_status[i]['id']}")
                sell_status.pop(0)
                
                if buy_status[i]['value'] == 0:
                    buy_status[i]['is_matched'] = True
                    buy_status[i]['is_open'] = False
                    buy_status[i]['is_partially_matched'] = False
            else:
                sell_status[0]['value'] -= buy_status[i]['value']
                buy_status[i]['value'] = 0
                buy_status[i]['is_matched'] = True
                buy_status[i]['is_open'] = False
                buy_status[i]['is_partially_matched'] = False

                logger.info(f"Partially matched Buy ID: {buy_status[i]['id']} with Sell ID: {sell_status[0]['id']}.")

            if buy_status[i]['value'] == 0:
                i += 1

        self.update_trade_status(buy_status)
        self.update_trade_status(sell_status)

    def update_trade_status(self, buy_status):
        for buy in buy_status:
            trade = TradeUploadBlofin.objects.get(id=buy['id'])
            trade.is_matched = buy['is_matched']
            trade.is_partially_matched = buy['is_partially_matched']
            trade.is_open = buy['is_open']
            trade.save()
            logger.info(f"Updated trade ID: {trade.id} with status: matched={buy['is_matched']}, partially_matched={buy['is_partially_matched']}, open={buy['is_open']}")

class TradeIdMatcher:
    def __init__(self, owner):
        self.owner = owner

    def check_trade_ids(self):
        trades = TradeUploadBlofin.objects.filter(owner=self.owner)

        asset_ids = {}

        for trade in trades:
            asset = trade.underlying_asset
            if asset:
                if asset not in asset_ids:
                    asset_ids[asset] = []
                asset_ids[asset].append(trade.id)

        logger.debug("Assets and their trade IDs:")
        for asset, ids in asset_ids.items():
            logger.debug(f"Asset: {asset}, Trade IDs: {ids}")

        # Initialize TradeMatcherProcessor
        processor = TradeMatcherProcessor(owner=self.owner)

        # Process each asset name that was found
        for asset_name in asset_ids.keys():
            processor.process_assets(asset_name, chunk_size=100)

        return asset_ids
