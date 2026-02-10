from pydantic import BaseModel


class Product(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category: str
    image_url: str
    in_stock: bool = True
    rating: float = 0.0


class CartItem(BaseModel):
    id: int
    product_id: int
    quantity: int


class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = 1


class SearchResponse(BaseModel):
    products: list[Product]
    total: int
    query: str


class HealthCheckResponse(BaseModel):
    status: str
    products_count: int
    uptime_seconds: float


class TranscribeResponse(BaseModel):
    text: str
    success: bool
    error: str | None = None
