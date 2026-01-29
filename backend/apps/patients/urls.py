from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, DiseaseViewSet

router = DefaultRouter()
router.register('diseases', DiseaseViewSet, basename='disease')
router.register('', PatientViewSet, basename='patient')

urlpatterns = [
    path('', include(router.urls)),
]
