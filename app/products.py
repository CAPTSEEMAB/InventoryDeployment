from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, HttpUrl
from .utils import ok, bad
from .auth import get_current_user
from .dynamodb_client import get_db_client
from .notifications import get_notification_service

router = APIRouter(prefix="/products", tags=["Products"])

try:
    db = get_db_client()
    notification = get_notification_service()
except Exception as e:
    raise RuntimeError(f"Failed to initialize services: {e}")

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: str = Field(..., min_length=1, max_length=1000, description="Product description")
    price: float = Field(..., gt=0, description="Product price (must be positive)")
    category: str = Field(..., min_length=1, max_length=100, description="Product category")
    sku: str = Field(..., min_length=1, max_length=50, description="Stock Keeping Unit (unique)")
    in_stock: int = Field(..., ge=0, description="Current stock quantity")
    reorder_level: int = Field(..., ge=0, description="Minimum stock level before reorder")
    supplier: str = Field(..., min_length=1, max_length=200, description="Supplier name")
    image_url: Optional[HttpUrl] = Field(None, description="Product image URL")

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Product name")
    description: Optional[str] = Field(None, min_length=1, max_length=1000, description="Product description")
    price: Optional[float] = Field(None, gt=0, description="Product price (must be positive)")
    category: Optional[str] = Field(None, min_length=1, max_length=100, description="Product category")
    sku: Optional[str] = Field(None, min_length=1, max_length=50, description="Stock Keeping Unit")
    in_stock: Optional[int] = Field(None, ge=0, description="Current stock quantity")
    reorder_level: Optional[int] = Field(None, ge=0, description="Minimum stock level")
    supplier: Optional[str] = Field(None, min_length=1, max_length=200, description="Supplier name")
    image_url: Optional[HttpUrl] = Field(None, description="Product image URL")
    is_active: Optional[bool] = Field(None, description="Whether product is active")

@router.get("/")
def get_all_products(current=Depends(get_current_user)):
    try:
        products = db.get_all_products(limit=100)
        return ok("Products fetched", products)
    except Exception as e:
        return bad(500, "DATABASE_ERROR", "Failed to fetch products", str(e))

@router.get("/search")
def search_products(query: str, current=Depends(get_current_user)):
    try:
        all_products = db.get_all_products(limit=1000)
        
        if not query:
            return ok("Search results", all_products)
        
        query_lower = query.lower()
        results = []
        
        for product in all_products:
            if (query_lower in product.get("name", "").lower() or
                query_lower in product.get("description", "").lower() or
                query_lower in product.get("category", "").lower() or
                query_lower in product.get("sku", "").lower()):
                results.append(product)
        
        return ok(f"Found {len(results)} products", results)
        
    except Exception as e:
        return bad(500, "DATABASE_ERROR", "Failed to search products", str(e))

@router.post("/", status_code=201)
def create_product(body: ProductCreate, current=Depends(get_current_user)):
    try:
        product_data = body.model_dump(mode="json")
        product_data = jsonable_encoder(product_data)
        
        product = db.create_product(product_data)
        
        try:
            notification_data = {
                **product,
                "created_by": current.get("email", "Unknown"),
                "created_by_name": current.get("name", "Unknown User")
            }
            
            result = notification.notify(
                action="created",
                resource="product",
                data=notification_data,
                priority="normal"
            )
            
            if result:
                print(f"Notification queued to SQS: {product.get('name')}")
            else:
                print(f"Notification queueing failed: {product.get('name')}")
                
        except Exception as notification_error:
            print(f"Notification exception: {notification_error}")
            import traceback
            traceback.print_exc()
        
        return ok("Product created successfully", product, status_code=201)
        
    except ValueError as e:
        return bad(400, "VALIDATION_ERROR", str(e))
    except Exception as e:
        return bad(500, "DATABASE_ERROR", "Failed to create product", str(e))

@router.get("/{product_id}")
def get_product_by_id(product_id: str, current=Depends(get_current_user)):
    try:
        product = db.get_product_by_id(product_id)
        if not product:
            return bad(404, "NOT_FOUND", "Product not found")
        
        return ok("Product found", product)
        
    except Exception as e:
        return bad(500, "DATABASE_ERROR", "Failed to fetch product", str(e))

@router.put("/{product_id}")
def update_product_by_id(product_id: str, body: ProductUpdate, current=Depends(get_current_user)):
    try:
        existing_product = db.get_product_by_id(product_id)
        if not existing_product:
            return bad(404, "NOT_FOUND", "Product not found")
        
        update_data = body.model_dump(mode="json", exclude_none=True)
        update_data = jsonable_encoder(update_data)
        
        if not update_data:
            return bad(400, "NO_DATA", "No update data provided")
        
        updated_product = db.update_product(product_id, update_data)
        
        # Send notification for product update
        try:
            notification.notify(
                action="updated",
                resource="product",
                data=updated_product,
                priority="normal"
            )
        except Exception:
            pass
        
        return ok("Product updated successfully", updated_product)
        
    except ValueError as e:
        return bad(400, "VALIDATION_ERROR", str(e))
    except Exception as e:
        return bad(500, "DATABASE_ERROR", "Failed to update product", str(e))

@router.delete("/{product_id}")
def delete_product_by_id(product_id: str, current=Depends(get_current_user)):
    try:
        existing_product = db.get_product_by_id(product_id)
        if not existing_product:
            return bad(404, "NOT_FOUND", "Product not found")
        
        try:
            notification_data = {
                **existing_product,
                "deleted_by": current.get("email", "Unknown"),
                "deleted_by_name": current.get("name", "Unknown User")
            }
            notification.notify(
                action="deleted",
                resource="product",
                data=notification_data,
                priority="high"  # High priority for deletions
            )
        except Exception:
            pass
        
        db.delete_product(product_id)
        return ok("Product deleted successfully", {"deleted_product_id": product_id})
        
    except Exception as e:
        return bad(500, "DATABASE_ERROR", "Failed to delete product", str(e))