from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Material(models.Model):
    name = models.CharField(max_length=150)
    material_code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.material_code} - {self.name}"

class Inventory(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="inventory")
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "material"],
                name="unique_material_per_warehouse",
            )
        ]

    def __str__(self):
        return f"{self.warehouse.code} / {self.material.material_code}: {self.quantity}"

class MaterialRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("PARTIALLY_FULFILLED", "Partially Fulfilled"),
        ("FULFILLED", "Fulfilled"),
    ]

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="material_requests",
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="requests")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDING")
    notes = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Request #{self.id} - {self.employee.username}"
    id = None

class RequestItem(models.Model):
    request = models.ForeignKey(
        MaterialRequest,
        on_delete=models.CASCADE,
        related_name="items",
    )
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["request", "material"],
                name="unique_material_per_request",
            )
        ]

    def __str__(self):
        return f"{self.request_id} / {self.material.material_code} x {self.quantity}"
    request_id = None
