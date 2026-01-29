"""
URL Configuration for Processing API.
"""

from django.urls import path
from . import views

app_name = 'processing'

urlpatterns = [
    path('document/', views.ProcessDocumentView.as_view(), name='process-document'),
    path('text/', views.ProcessTextView.as_view(), name='process-text'),
    path('batch/', views.ProcessBatchView.as_view(), name='process-batch'),
    path('status/', views.ProcessingStatusView.as_view(), name='process-status'),
]
