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
from django.db.models import Count


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
        file_name = request.query_params.get('file_name')
        
        if not file_name:
            return Response({"detail": "File name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete trades for the specific file name
        trades_deleted, _ = TradeUploadBlofin.objects.filter(file_name=file_name).delete()
        
        # Also delete the file name record from FileName model
        file_name_record = FileName.objects.filter(file_name=file_name)
        if file_name_record.exists():
            file_name_record.delete()
        
        return Response({
            "message": f"{trades_deleted} trades for file '{file_name}' deleted."
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

        owner = request.user

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['file']
        file_name = file.name # Capture the file name
        exchange = serializer.validated_data.get('exchange', None)

        if exchange != 'BloFin':
            return Response({"error": "Sorry, under construction."}, status=status.HTTP_400_BAD_REQUEST)

        # Process the CSV using the CSVProcessor class
        processor = CsvProcessor(owner, exchange)
        result = processor.process_csv_file(file, file_name)

        if isinstance(result, Response):
            return result  # Return early if an error occurred during CSV processing

        new_trades_count, duplicates, canceled_count = result

        # Update FileName model
        file_name_entry, created = FileName.objects.get_or_create(owner=owner, file_name=file_name)
        file_name_entry.trade_count += new_trades_count
        file_name_entry.save()

        end_time = time.time()  # End timing
        elapsed_time = end_time - start_time  # Calculate the elapsed time

        response_message = {
            "status": "success",
            "message": f"{new_trades_count} new trades added, {duplicates} duplicates found,  {canceled_count} canceled trades ignored.",
            "time_taken": f"{elapsed_time:.2f} seconds"
        }

        return Response(response_message, status=status.HTTP_201_CREATED)
