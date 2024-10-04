from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import pandas as pd
import time
from .serializers import FileUploadSerializer, SaveTradeSerializer, FileNameSerializer
from django_filters.rest_framework import DjangoFilterBackend
from upload_csv.exchange.blofin.blofin_csv_handler import BloFinHandler
from upload_csv.exchange.blofin.csv_processor import CsvProcessor
from .models import TradeUploadBlofin, FileName
from .tasks import  process_trade_ids_in_background, process_asset_in_background
from .trade_matcher import TradeIdMatcher
from django.db.models import Count
import logging

logger = logging.getLogger(__name__) 

class CsvTradeView(generics.ListAPIView):
    serializer_class = SaveTradeSerializer
    permission_classes = [IsAuthenticated]
    queryset = TradeUploadBlofin.objects.all().order_by('-order_time')
    filter_backends = [DjangoFilterBackend,
                       filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['owner__username',
                     'underlying_asset', 'side', 'file_name']
    ordering_fields = ['owner', 'order_time',
                       'underlying_asset', 'side', 'is_open', 'is_matched']
    ordering = ['-order_time']


class FileNameListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FileNameSerializer

    def get_queryset(self):
        return FileName.objects.all().order_by('file_name')


class DeleteTradesByFileNameView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        file_id = kwargs.get('pk')

        if not file_id:
            return Response({"detail": "File ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the FileName entry by ID
        try:
            file_name_entry = FileName.objects.get(id=file_id)
        except FileName.DoesNotExist:
            return Response({"detail": "File not found."}, status=status.HTTP_404_NOT_FOUND)

        # Delete trades for the specific file name
        trade_count, _ = TradeUploadBlofin.objects.filter(
            file_name=file_name_entry.file_name).delete()

        # Delete the FileName entry itself
        file_name_entry.delete()

        return Response({
            "message": f"{trade_count} trades for file '{file_name_entry.file_name}' deleted."
        }, status=status.HTTP_204_NO_CONTENT)


class UploadFileView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FileUploadSerializer
    http_method_names = ['post', 'options', 'head']

    def options(self, request, *args, **kwargs):
        logger.debug(f"Handling OPTIONS request. Headers: {request.headers}")
        return Response(status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        return Response({"detail": "Method 'GET' not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def post(self, request, *args, **kwargs):
        start_time = time.time()
        logger.debug("Starting the post request.")

        owner = request.user
        logger.debug(f"Request owner: {owner.username}")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data['file']
        file_name = file.name  # Capture the file name
        logger.debug(f"File name received: {file_name}")

        exchange = serializer.validated_data.get('exchange', None)

        if exchange != 'BloFin':
            logger.error("Invalid exchange provided.")
            return Response({"error": "Sorry, under construction."}, status=status.HTTP_400_BAD_REQUEST)

        # Process the CSV using the CSVProcessor class
        processor = CsvProcessor(owner, exchange)
        logger.debug("Processing CSV file.")
        result = processor.process_csv_file(file, file_name)

        if isinstance(result, Response):
            logger.error("CSV processing error occurred.")
            return result  # Return early if an error occurred during CSV processing

        new_trades_count, duplicates, canceled_count = result
        logger.debug(f"New trades count: {new_trades_count}, Duplicates: {duplicates}, Canceled: {canceled_count}")


        # Fetch asset names from BlofinModel for the current user
        asset_names = TradeUploadBlofin.objects.filter(owner=owner).values_list('underlying_asset', flat=True)  # Replace 'asset_name' with the actual field name
        logger.debug(f"Retrieved asset names: {list(asset_names)}")  # Log the asset names

        for asset_name in asset_names:  # Loop through each asset name
            process_trade_ids_in_background.delay(owner.id)  # Process each asset
            process_asset_in_background(owner.id, asset_name)
            logger.debug(f"Triggered background task for asset processing: {asset_name}")


        # Update FileName model
        file_name_entry, created = FileName.objects.get_or_create(owner=owner, file_name=file_name)
        file_name_entry.trade_count += new_trades_count
        file_name_entry.save()
        logger.debug(f"Updated file name entry: {file_name_entry.file_name}, Trade count: {file_name_entry.trade_count}")

        # matcher_id = TradeIdMatcher(owner)
        # matcher_id.check_trade_ids()

        end_time = time.time()  # End timing
        elapsed_time = end_time - start_time  # Calculate the elapsed time

        response_message = {
            "status": "success",
            "message": f"{new_trades_count} new trades added, {duplicates} duplicates found, {canceled_count} canceled trades ignored.",
            "time_taken": f"{elapsed_time:.2f} seconds"
        }

        logger.debug(f"Response message: {response_message}")
        return Response(response_message, status=status.HTTP_201_CREATED)
