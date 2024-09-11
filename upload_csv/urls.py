from django.urls import path
from .views import UploadFileView, CsvTradeView, DeleteAllTradesAndLiveTradesView
urlpatterns = [
    path('upload/', UploadFileView.as_view(), name='upload-file'),
    path('trades-csv/', CsvTradeView.as_view(), name='csv-trade'),
    path('trades-delete/', DeleteAllTradesAndLiveTradesView.as_view(), name='delete-all-trades-and-live-trades'),
]