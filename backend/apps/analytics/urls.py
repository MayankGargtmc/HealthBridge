from django.urls import path
from .views import DashboardView, DiseaseAnalyticsView, LocationAnalyticsView, AgeAnalyticsView

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('diseases/', DiseaseAnalyticsView.as_view(), name='disease-analytics'),
    path('locations/', LocationAnalyticsView.as_view(), name='location-analytics'),
    path('age/', AgeAnalyticsView.as_view(), name='age-analytics'),
]
