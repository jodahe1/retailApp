# Phase 3 - Product Management Testing Guide

## Prerequisites
1. Server running: `uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload`
2. Database tables created
3. Swagger UI open: `http://localhost:8001/docs`

## Step-by-Step Testing

### Step 1: Create Admin User with Permissions

```bash
# 1. Create a user
curl -X POST http://localhost:8001/api/v1/auth/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin1234"
  }'

# 2. Login to get token
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin1234"
  }'
```

Save the `access_token` from the response.

### Step 2: Create Permissions and Assign to User

In Swagger UI (`http://localhost:8001/docs`):

1. Click "Authorize" button at top
2. Enter: `Bearer YOUR_ACCESS_TOKEN`
3. Click "Authorize"

Then create permissions:

**POST /api/v1/admin/permissions**
```json
{
  "code": "product:manage",
  "description": "Manage products"
}
```

**POST /api/v1/admin/permissions**
```json
{
  "code": "product:retrieve",
  "description": "Retrieve products"
}
```

**POST /api/v1/admin/permissions**
```json
{
  "code": "checkout:item:add",
  "description": "Add items to checkout"
}
```

### Step 3: Create Role and Assign Permissions

**POST /api/v1/admin/roles**
```json
{
  "name": "cashier",
  "description": "Cashier role"
}
```

**POST /api/v1/admin/roles/{role_id}/permissions**
```json
{
  "permission_ids": [1, 2, 3]
}
```
(Use the actual permission IDs from Step 2)

### Step 4: Assign Role to User

**POST /api/v1/admin/users/{user_id}/roles**
```json
{
  "role_ids": [1]
}
```
(Use your user_id and role_id)

### Step 5: Create Products

**POST /api/v1/products**
```json
{
  "name": "Orange Juice 1L",
  "name_pinyin": "chengzhi",
  "barcode": "6901234567890",
  "internal_code": "OJ001",
  "unit_price": 15.50,
  "stock_quantity": 100
}
```

**POST /api/v1/products**
```json
{
  "name": "Apple Juice 500ml",
  "name_pinyin": "pingguozhi",
  "barcode": "6901234567891",
  "internal_code": "AJ001",
  "unit_price": 12.00,
  "stock_quantity": 50
}
```

**POST /api/v1/products**
```json
{
  "name": "Mineral Water 1.5L",
  "name_pinyin": "kuangquanshui",
  "barcode": "6901234567892",
  "internal_code": "MW001",
  "unit_price": 3.50,
  "stock_quantity": 200
}
```

### Step 6: Test Product Retrieval

**GET /api/v1/products/retrieve?barcode=6901234567890**
- Should return Orange Juice

**GET /api/v1/products/retrieve?internal_code=AJ001**
- Should return Apple Juice

**GET /api/v1/products/retrieve?name_pinyin=kuangquanshui**
- Should return Mineral Water

### Step 7: Test Quick Match (Cashier Search)

**POST /api/v1/products/quick-match**
```json
{
  "query": "6901234567890",
  "limit": 10
}
```
- Should return Orange Juice

**POST /api/v1/products/quick-match**
```json
{
  "query": "cheng",
  "limit": 10
}
```
- Should return products with pinyin starting with "cheng"

### Step 8: Test Pre-Checkout Item Building

**POST /api/v1/products/precheckout/items**
```json
{
  "product_id": 1,
  "quantity": 2
}
```
- Should return item details with calculated subtotal

### Step 9: Test Product Status Management

**PATCH /api/v1/products/1/status**
```json
{
  "is_active": false
}
```
- Product becomes inactive

Now try to retrieve it:
**GET /api/v1/products/retrieve?barcode=6901234567890**
- Should fail with "Product is inactive"

Reactivate it:
**PATCH /api/v1/products/1/status**
```json
{
  "is_active": true,
  "is_available_for_sale": false
}
```

Try pre-checkout:
**POST /api/v1/products/precheckout/items**
```json
{
  "product_id": 1,
  "quantity": 2
}
```
- Should fail with "Product not available for sale"

### Step 10: Test Authorization

Logout and create a new user without permissions:

```bash
curl -X POST http://localhost:8001/api/v1/auth/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "guest",
    "password": "Guest1234"
  }'

curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "guest",
    "password": "Guest1234"
  }'
```

Use the guest token and try:
**POST /api/v1/products**
- Should fail with "Permission denied"

## Expected Results Summary

✅ Products can be created with barcode, internal_code, pinyin
✅ Products can be retrieved by barcode/internal_code/pinyin
✅ Quick match works for cashier search
✅ Pre-checkout validates product status
✅ Inactive products are rejected
✅ Unavailable products cannot be added to checkout
✅ Authorization checks work (permission required)
✅ Failed scans are logged

## Check Logs

Look for boundary logging in the console:
- Failed product retrievals
- Invalid barcode scans
- Authorization failures
