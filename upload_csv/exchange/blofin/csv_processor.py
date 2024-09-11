import pandas as pd
import logging
from rest_framework.response import Response
from rest_framework import status
import time

logger = logging.getLogger(__name__)

class CSVProcessor:
    def __init__(self, owner, exchange):
        self.owner = owner
        self.exchange = exchange

    def process_csv_file(self, file):
        try:
            reader = pd.read_csv(file)
            logger.debug(f"CSV file read successfully. Number of rows: {len(reader)}")
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            return Response({"error": "Error reading CSV file."}, status=status.HTTP_400_BAD_REQUEST)

        required_columns = {'Underlying Asset', 'Margin Mode', 'Leverage', 'Order Time', 'Side', 'Avg Fill',
                            'Price', 'Filled', 'Total', 'PNL', 'PNL%', 'Fee', 'Order Options', 'Reduce-only', 'Status'}
        missing_cols = required_columns - set(reader.columns)
        if missing_cols:
            logger.warning(f"Missing columns: {', '.join(missing_cols)}")
            return Response({"error": f"Missing Columns: {', '.join(missing_cols)}"})

        unexpected_cols = set(reader.columns) - required_columns
        if unexpected_cols:
            logger.warning(f"Unexpected columns found: {', '.join(unexpected_cols)}")
            return Response({"error": f"Unexpected columns found: {', '.join(unexpected_cols)}"}, status=status.HTTP_400_BAD_REQUEST)

        csv_data = reader.to_dict('records')
        logger.debug(f"CSV data converted to list of dictionaries. Number of records: {len(csv_data)}")

        handler = BloFinHandler()
        processor = CsvProcessor(handler)
        trade_updater = TradeUpdater(self.owner)

        logger.debug(f"Starting CSV processing.")
        new_trades_count, duplicates, canceled_count = processor.process_csv_data(csv_data, self.owner, self.exchange)
        logger.debug(f"CSV processing complete. New trades count: {new_trades_count}, Duplicates: {duplicates}, Canceled count: {canceled_count}")

        live_price_fetches_count = trade_updater.count_open_trades_for_price_fetch()
        logger.debug(f"Live price fetches count: {live_price_fetches_count}")

        return new_trades_count, duplicates, canceled_count, live_price_fetches_count
