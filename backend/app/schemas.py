from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "customer"


class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class RestaurantResponse(BaseModel):
    id: int
    name: str
    cuisine: str
    owner_id: int | None

    class Config:
        from_attributes = True


class MenuItemCreate(BaseModel):
    restaurant_id: int
    name: str
    price: float


class MenuItemResponse(BaseModel):
    id: int
    restaurant_id: int
    name: str
    price: float

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    restaurant_id: int
    menu_item_id: int | None = None


class OrderResponse(BaseModel):
    id: int
    user_id: int
    restaurant_id: int
    restaurant_name: str | None = None

    menu_item_id: int | None
    menu_item_name: str | None = None

    rider_id: int | None
    status: str

    class Config:
        from_attributes = True