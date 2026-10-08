# Warehouse Material Request System

Django REST Framework + JavaScript assessment project.

## Features

- Employee and warehouse employee registration/login
- Token authentication
- Multiple warehouses
- Materials and inventory
- Search inventory across warehouses
- Create requests containing multiple materials
- Request status tracking
- Warehouse approval/rejection
- Warehouse fulfillment
- Transaction-safe inventory deduction using `select_for_update()`
- Django admin

## Setup

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install:

```bash
pip install -r requirements.txt
```

Create database:

```bash
python manage.py makemigrations
python manage.py migrate
```

Create admin:

```bash
python manage.py createsuperuser
```

Start:

```bash
python manage.py runserver
```

Open:

http://127.0.0.1:8000/

Admin:

http://127.0.0.1:8000/admin/

## Add sample data

Use Django admin to create:

1. Warehouses
2. Materials
3. Inventory records

For every warehouse/material combination, create an Inventory record.

Example:

Warehouse:
- WH01 / Main Warehouse / Salem
- WH02 / Branch Warehouse / Chennai

Materials:
- MAT001 / Steel Rod
- MAT002 / Copper Wire

Inventory:
- WH01 + MAT001 = 100
- WH02 + MAT001 = 75
- WH01 + MAT002 = 50

## Test flow

1. Register an Employee.
2. Register a Warehouse Employee.
3. Login as employee.
4. Search materials.
5. Select a warehouse.
6. Add multiple materials to the request.
7. Submit.
8. Login as warehouse employee.
9. Approve the request.
10. Fulfill the request.
11. Verify inventory decreased.
12. Try fulfilling a request where quantity is greater than available inventory.

## Concurrency

The fulfillment API uses:

```python
transaction.atomic()
Inventory.objects.select_for_update()
```

This locks the relevant inventory rows while the transaction is processed. Therefore two simultaneous fulfillment requests cannot both consume the same inventory quantity.

## Important production note

The example uses SQLite to make local setup easy. For production or a real assessment deployment, PostgreSQL is recommended for stronger concurrent transaction behavior.
