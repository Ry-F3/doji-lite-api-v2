from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, filters, status
from rest_framework.response import Response
from django.utils import timezone
import pandas as pd
import time
from .serializers import FileUploadSerializer, SaveTradeSerializer, FileNameSerializer
from django_filters.rest_framework import DjangoFilterBackend
from upload_csv.exchange.blofin.blofin_csv_handler import BloFinHandler
from upload_csv.exchange.blofin.csv_processor import CsvProcessor
from .models import TradeUploadBlofin, FileName
from .tasks import  process_trade_ids_in_background, process_asset_in_background, process_csv_file_async
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
        force_delete = request.query_params.get('force', 'false') == 'true'

        if not file_id:
            return Response({"detail": "File ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            file_name_entry = FileName.objects.get(id=file_id)
        except FileName.DoesNotExist:
            return Response({"detail": "File not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if the file is currently processing
        if not force_delete and file_name_entry.cancel_processing:
            return Response({"detail": "File is currently processing and cannot be deleted."}, status=status.HTTP_403_FORBIDDEN)

        # Allow deletion
        trade_count, _ = TradeUploadBlofin.objects.filter(file_name=file_name_entry.file_name).delete()
        file_name_entry.delete()

        return Response({
            "message": f"{trade_count} trades for file '{file_name_entry.file_name}' deleted."
        }, status=status.HTTP_204_NO_CONTENT)


class DeleteAllTradesView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        owner = request.user
        force_delete = request.query_params.get('force', 'false') == 'true'

        # Check if the force delete flag is set
        if not force_delete:
            # Implement your check logic here if needed
            # For example, checking if any trades are currently being processed
            if TradeUploadBlofin.objects.filter(owner=owner, is_processing=True).exists():
                return Response({"detail": "Cannot delete trades while they are being processed."}, status=status.HTTP_403_FORBIDDEN)

        # Delete all trades for the authenticated user
        trade_count, _ = TradeUploadBlofin.objects.filter(owner=owner).delete()

        return Response({
            "message": f"Successfully deleted {trade_count} trades."
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


        # Update FileName model
        file_name_entry, created = FileName.objects.get_or_create(owner=owner, file_name=file_name)
        file_name_entry.trade_count += new_trades_count
        file_name_entry.save()
        logger.debug(f"Updated file name entry: {file_name_entry.file_name}, Trade count: {file_name_entry.trade_count}")

        # Push CSV processing to the background using Celery
        process_csv_file_async.delay(owner.id, file_name_entry.id, file.read().decode('utf-8'), exchange)


        end_time = time.time()  # End timing
        elapsed_time = end_time - start_time  # Calculate the elapsed time

        response_message = {
            "status": "success",
            "message": f"{new_trades_count} new trades added, {duplicates} duplicates found, {canceled_count} canceled trades ignored.",
            "time_taken": f"{elapsed_time:.2f} seconds"
        }

        logger.debug(f"Response message: {response_message}")
        return Response(response_message, status=status.HTTP_201_CREATED)

    