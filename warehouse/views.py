from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Warehouse, Material, Inventory, MaterialRequest, RequestItem
from .serializers import (
    WarehouseSerializer, MaterialSerializer, InventorySerializer,
    MaterialRequestSerializer, MaterialRequestCreateSerializer,
)

def is_warehouse_employee(user):
    profile = getattr(user, "profile", None)
    return user.is_staff or (profile and profile.role == "WAREHOUSE")

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by("name")
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all().order_by("name")
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(material_code__icontains=search)
        return qs.distinct()

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.select_related("warehouse", "material").all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        material = self.request.query_params.get("material")
        warehouse = self.request.query_params.get("warehouse")
        search = self.request.query_params.get("search", "").strip()
        if material:
            qs = qs.filter(material_id=material)
        if warehouse:
            qs = qs.filter(warehouse_id=warehouse)
        if search:
            qs = qs.filter(material__name__icontains=search) | qs.filter(
                material__material_code__icontains=search
            )
        return qs

    def create(self, request, *args, **kwargs):
        if not is_warehouse_employee(request.user):
            return Response({"detail": "Only warehouse employees can change inventory."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not is_warehouse_employee(request.user):
            return Response({"detail": "Only warehouse employees can change inventory."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not is_warehouse_employee(request.user):
            return Response({"detail": "Only warehouse employees can change inventory."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

class MaterialRequestViewSet(viewsets.ModelViewSet):
    queryset = MaterialRequest.objects.select_related(
        "employee", "warehouse"
    ).prefetch_related("items__material").all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return MaterialRequestCreateSerializer
        return MaterialRequestSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if is_warehouse_employee(self.request.user):
            return qs
        return qs.filter(employee=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            material_request = MaterialRequest.objects.create(
                employee=request.user,
                warehouse_id=data["warehouse"],
                notes=data.get("notes", ""),
            )
            RequestItem.objects.bulk_create([
                RequestItem(
                    request=material_request,
                    material_id=item["material"],
                    quantity=item["quantity"],
                )
                for item in data["items"]
            ])

        output = MaterialRequestSerializer(material_request)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not is_warehouse_employee(request.user):
            return Response({"detail": "Warehouse employee access required."}, status=403)

        material_request = self.get_object()
        if material_request.status != "PENDING":
            return Response({"detail": "Only pending requests can be approved."}, status=400)

        material_request.status = "APPROVED"
        material_request.save(update_fields=["status"])
        return Response(MaterialRequestSerializer(material_request).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not is_warehouse_employee(request.user):
            return Response({"detail": "Warehouse employee access required."}, status=403)

        material_request = self.get_object()
        if material_request.status not in ["PENDING", "APPROVED"]:
            return Response({"detail": "This request cannot be rejected now."}, status=400)

        material_request.status = "REJECTED"
        material_request.save(update_fields=["status"])
        return Response(MaterialRequestSerializer(material_request).data)

    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None):
        if not is_warehouse_employee(request.user):
            return Response({"detail": "Warehouse employee access required."}, status=403)

        with transaction.atomic():
            material_request = (
                MaterialRequest.objects
                .select_for_update()
                .prefetch_related("items")
                .get(pk=pk)
            )

            if material_request.status not in ["PENDING", "APPROVED"]:
                return Response(
                    {"detail": "Only pending or approved requests can be fulfilled."},
                    status=400,
                )

            items = list(material_request.items.all())

            # Lock all relevant inventory rows before checking quantities.
            inventory_map = {}
            for item in items:
                try:
                    inventory = (
                        Inventory.objects
                        .select_for_update()
                        .get(
                            warehouse=material_request.warehouse,
                            material=item.material,
                        )
                    )
                except Inventory.DoesNotExist:
                    return Response(
                        {"detail": f"No inventory record for {item.material.name}."},
                        status=400,
                    )
                inventory_map[item.material_id] = inventory

            insufficient = []
            for item in items:
                inventory = inventory_map[item.material_id]
                if inventory.quantity < item.quantity:
                    insufficient.append({
                        "material": item.material.name,
                        "requested": item.quantity,
                        "available": inventory.quantity,
                    })

            if insufficient:
                return Response({
                    "detail": "Insufficient inventory. No inventory was changed.",
                    "items": insufficient,
                }, status=409)

            for item in items:
                inventory = inventory_map[item.material_id]
                inventory.quantity -= item.quantity
                inventory.save(update_fields=["quantity"])

            material_request.status = "FULFILLED"
            material_request.fulfilled_at = timezone.now()
            material_request.save(update_fields=["status", "fulfilled_at"])

        return Response(MaterialRequestSerializer(material_request).data)
