from django.urls import path
from .views import UploadFileView, CsvTradeView, DeleteTradesByFileNameView, FileNameListView, DeleteAllTradesView, TradeProcessingStatusList, TradeProcessingStatusDetail
urlpatterns = [
    path('upload/', UploadFileView.as_view(), name='upload-file'),
    path('trades-csv/', CsvTradeView.as_view(), name='csv-trade'),
    path('trades-csv/delete-all/', DeleteAllTradesView.as_view(), name='delete-all-trades'),
    path('filenames/', FileNameListView.as_view(), name='file-names'),
    path('filenames/delete/<int:pk>/', DeleteTradesByFileNameView.as_view(), name='delete-trades'),
    path('trade-status/', TradeProcessingStatusList.as_view(), name='trade-processing-status-list'),  # List and create
    path('trade-status/<int:pk>/', TradeProcessingStatusDetail.as_view(), name='trade-processing-status-detail'),  # Retrieve, update, delete
]