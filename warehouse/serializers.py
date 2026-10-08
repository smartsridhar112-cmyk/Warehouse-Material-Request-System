from rest_framework import serializers
from .models import Warehouse, Material, Inventory, MaterialRequest, RequestItem

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "code", "name", "location"]

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = ["id", "material_code", "name", "description"]

class InventorySerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    material_name = serializers.CharField(source="material.name", read_only=True)
    material_code = serializers.CharField(source="material.material_code", read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "id", "warehouse", "warehouse_name", "warehouse_code",
            "material", "material_name", "material_code", "quantity"
        ]

class RequestItemSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source="material.name", read_only=True)
    material_code = serializers.CharField(source="material.material_code", read_only=True)

    class Meta:
        model = RequestItem
        fields = ["id", "material", "material_name", "material_code", "quantity"]

class RequestItemCreateSerializer(serializers.Serializer):
    material = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class MaterialRequestSerializer(serializers.ModelSerializer):
    items = RequestItemSerializer(many=True, read_only=True)
    employee_name = serializers.CharField(source="employee.username", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)

    class Meta:
        model = MaterialRequest
        fields = [
            "id", "employee", "employee_name", "warehouse",
            "warehouse_name", "warehouse_code", "status", "notes",
            "requested_at", "fulfilled_at", "items"
        ]
        read_only_fields = [
            "employee", "status", "requested_at", "fulfilled_at"
        ]

class MaterialRequestCreateSerializer(serializers.Serializer):
    warehouse = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)
    items = RequestItemCreateSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        material_ids = [item["material"] for item in attrs["items"]]
        if len(material_ids) != len(set(material_ids)):
            raise serializers.ValidationError("A material can appear only once in a request.")
        if not Warehouse.objects.filter(id=attrs["warehouse"]).exists():
            raise serializers.ValidationError({"warehouse": "Warehouse not found."})
        missing = set(material_ids) - set(Material.objects.filter(id__in=material_ids).values_list("id", flat=True))
        if missing:
            raise serializers.ValidationError({"items": f"Invalid material IDs: {sorted(missing)}"})
        return attrs
