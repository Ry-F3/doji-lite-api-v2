from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import pandas as pd
import time
from .serializers import FileUploadSerializer, SaveTradeSerializer
from django_filters.rest_framework import DjangoFilterBackend
from upload_csv.exchange.blofin.blofin_csv_handler import BloFinHandler
from upload_csv.exchange.blofin.csv_processor import CsvProcessor
from .models import TradeUploadBlofin


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


class DeleteAllTradesAndLiveTradesView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        # Delete all trades
        trade_count, _ = TradeUploadBlofin.objects.all().delete()
        # Delete all live trades
        # live_trade_count, _ = LiveTrades.objects.all().delete()

        return Response({
            "message": f"{trade_count} trades live trades deleted."
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
        exchange = serializer.validated_data.get('exchange', None)

        if exchange != 'BloFin':
            return Response({"error": "Sorry, under construction."}, status=status.HTTP_400_BAD_REQUEST)

        # Process the CSV using the CSVProcessor class
        processor = CsvProcessor(owner, exchange)
        result = processor.process_csv_file(file)

        if isinstance(result, Response):
            return result  # Return early if an error occurred during CSV processing

        new_trades_count, duplicates, canceled_count = result

        end_time = time.time()  # End timing
        elapsed_time = end_time - start_time  # Calculate the elapsed time

        response_message = {
            "status": "success",
            "message": f"{new_trades_count} new trades added, {duplicates} duplicates found,  {canceled_count} canceled trades ignored.",
            "time_taken": f"{elapsed_time:.2f} seconds"
        }

        return Response(response_message, status=status.HTTP_201_CREATED)
