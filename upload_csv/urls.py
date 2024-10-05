from django.urls import path
from .views import UploadFileView, CsvTradeView, DeleteTradesByFileNameView, FileNameListView, DeleteAllTradesView
urlpatterns = [
    path('upload/', UploadFileView.as_view(), name='upload-file'),
    path('trades-csv/', CsvTradeView.as_view(), name='csv-trade'),
    path('trades-csv/delete-all/', DeleteAllTradesView.as_view(), name='delete-all-trades'),
    path('filenames/', FileNameListView.as_view(), name='file-names'),
    path('filenames/delete/<int:pk>/', DeleteTradesByFileNameView.as_view(), name='delete-trades'),
]