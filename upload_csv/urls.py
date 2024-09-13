from django.urls import path
from .views import UploadFileView, CsvTradeView, DeleteTradesByFileNameView, FileNameListView
urlpatterns = [
    path('upload/', UploadFileView.as_view(), name='upload-file'),
    path('trades-csv/', CsvTradeView.as_view(), name='csv-trade'),
    path('filenames/', FileNameListView.as_view(), name='file-names'),
    path('filenames/delete/<int:pk>/', DeleteTradesByFileNameView.as_view(), name='delete-trades'),
]