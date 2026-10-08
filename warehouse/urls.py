from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, MaterialViewSet, InventoryViewSet, MaterialRequestViewSet

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("materials", MaterialViewSet, basename="material")
router.register("inventory", InventoryViewSet, basename="inventory")
router.register("requests", MaterialRequestViewSet, basename="request")

urlpatterns = router.urls
