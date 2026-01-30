from django.urls import path
from .views import (
    DashboardView, 
    DiseaseAnalyticsView, 
    LocationAnalyticsView, 
    AgeAnalyticsView,
    SurveillanceView,
    DiseaseTrendsView,
    ComorbidityView,
    AdvancedFiltersView,
    FilterOptionsView,
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('diseases/', DiseaseAnalyticsView.as_view(), name='disease-analytics'),
    path('locations/', LocationAnalyticsView.as_view(), name='location-analytics'),
    path('age/', AgeAnalyticsView.as_view(), name='age-analytics'),
    
    # New surveillance endpoints
    path('surveillance/', SurveillanceView.as_view(), name='surveillance'),
    path('trends/', DiseaseTrendsView.as_view(), name='disease-trends'),
    path('comorbidity/', ComorbidityView.as_view(), name='comorbidity'),
    path('filters/', AdvancedFiltersView.as_view(), name='advanced-filters'),
    path('filter-options/', FilterOptionsView.as_view(), name='filter-options'),
]
