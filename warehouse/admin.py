from django.contrib import admin
from .models import Warehouse, Material, Inventory, MaterialRequest, RequestItem

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "location")
    search_fields = ("code", "name", "location")

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("material_code", "name")
    search_fields = ("material_code", "name")

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("warehouse", "material", "quantity")
    list_filter = ("warehouse",)
    search_fields = ("material__name", "material__material_code")

class RequestItemInline(admin.TabularInline):
    model = RequestItem
    extra = 0

@admin.register(MaterialRequest)
class MaterialRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "warehouse", "status", "requested_at", "fulfilled_at")
    list_filter = ("status", "warehouse")
    search_fields = ("employee__username",)
    inlines = [RequestItemInline]
