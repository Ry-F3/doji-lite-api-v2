import pandas as pd
from rest_framework.response import Response
from upload_csv.exchange.blofin.blofin_csv_handler import BloFinHandler, CsvCopyProcessor
from rest_framework import status
import time


class CsvProcessor:
    def __init__(self, owner, exchange):
        self.owner = owner
        self.exchange = exchange

    def process_csv_file(self, file, file_name):
        try:
            reader = pd.read_csv(file)
        except Exception as e:
            raise ValueError("Error reading CSV file.") from e

        required_columns = {
            'Underlying Asset', 'Margin Mode', 'Leverage', 'Order Time', 'Side', 
            'Avg Fill', 'Price', 'Filled', 'Total', 'PNL', 'PNL%', 'Fee', 
            'Order Options', 'Reduce-only', 'Status'
        }

        missing_cols = required_columns - set(reader.columns)
        if missing_cols:
            raise ValueError(f"Missing Columns: {', '.join(missing_cols)}")

        unexpected_cols = set(reader.columns) - required_columns
        if unexpected_cols:
            raise ValueError(f"Unexpected columns found: {', '.join(unexpected_cols)}")

        # Validate data types or specific content if necessary

        csv_data = reader.to_dict('records')

        handler = BloFinHandler()
        processor = CsvCopyProcessor(handler)

        new_trades_count, duplicates, canceled_count = processor.process_csv_data(
            csv_data, self.owner, self.exchange, file_name
        )

        return new_trades_count, duplicates, canceled_count
