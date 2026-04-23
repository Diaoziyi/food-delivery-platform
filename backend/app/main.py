from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from . import models, schemas
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

app = FastAPI()

Base.metadata.create_all(bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_restaurants():
    db = SessionLocal()
    try:
        count = db.query(models.Restaurant).count()
        if count == 0:
            restaurants = [
                models.Restaurant(name="Burger House", cuisine="Burgers"),
                models.Restaurant(name="Sushi World", cuisine="Japanese"),
                models.Restaurant(name="Pasta Corner", cuisine="Italian"),
            ]
            db.add_all(restaurants)
            db.commit()
    finally:
        db.close()


seed_restaurants()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def require_role(user: models.User, allowed_roles: list[str]):
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )


@app.get("/")
def read_root():
    return {"message": "Food delivery backend is running!"}


@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(models.User)
        .filter(models.User.username == user.username)
        .first()
    )

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = models.User(
        username=user.username,
        password=hash_password(user.password),
        role=user.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login", response_model=schemas.TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(models.User)
        .filter(models.User.username == form_data.username)
        .first()
    )

    if not existing_user or not verify_password(form_data.password, existing_user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(
        {"sub": existing_user.username, "role": existing_user.role}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@app.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.get("/restaurants", response_model=list[schemas.RestaurantResponse])
def get_restaurants(db: Session = Depends(get_db)):
    return db.query(models.Restaurant).all()


@app.get("/restaurants/{restaurant_id}/menu", response_model=list[schemas.MenuItemResponse])
def get_restaurant_menu(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = (
        db.query(models.Restaurant)
        .filter(models.Restaurant.id == restaurant_id)
        .first()
    )
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return (
        db.query(models.MenuItem)
        .filter(models.MenuItem.restaurant_id == restaurant_id)
        .all()
    )


@app.post("/owner/restaurants/{restaurant_id}/claim", response_model=schemas.RestaurantResponse)
def claim_restaurant(
    restaurant_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, ["restaurant_owner"])

    restaurant = (
        db.query(models.Restaurant)
        .filter(models.Restaurant.id == restaurant_id)
        .first()
    )
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if restaurant.owner_id is not None and restaurant.owner_id != current_user.id:
        raise HTTPException(status_code=400, detail="Restaurant already claimed")

    restaurant.owner_id = current_user.id
    db.commit()
    db.refresh(restaurant)
    return restaurant


@app.post("/owner/menu-items", response_model=schemas.MenuItemResponse)
def create_menu_item(
    item: schemas.MenuItemCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, ["restaurant_owner"])

    restaurant = (
        db.query(models.Restaurant)
        .filter(
            models.Restaurant.id == item.restaurant_id,
            models.Restaurant.owner_id == current_user.id
        )
        .first()
    )
    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found or not owned by current user",
        )

    menu_item = models.MenuItem(
        restaurant_id=item.restaurant_id,
        name=item.name,
        price=item.price,
    )
    db.add(menu_item)
    db.commit()
    db.refresh(menu_item)
    return menu_item


@app.get("/owner/menu-items", response_model=list[schemas.MenuItemResponse])
def get_owner_menu_items(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, ["restaurant_owner"])

    owned_restaurants = (
        db.query(models.Restaurant.id)
        .filter(models.Restaurant.owner_id == current_user.id)
        .all()
    )
    restaurant_ids = [r[0] for r in owned_restaurants]

    if not restaurant_ids:
        return []

    return (
        db.query(models.MenuItem)
        .filter(models.MenuItem.restaurant_id.in_(restaurant_ids))
        .all()
    )


@app.post("/orders", response_model=schemas.OrderResponse)
def create_order(
    order: schemas.OrderCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, ["customer"])

    # 检查餐厅是否存在
    restaurant = (
        db.query(models.Restaurant)
        .filter(models.Restaurant.id == order.restaurant_id)
        .first()
    )
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # 检查菜品是否属于该餐厅
    if order.menu_item_id is not None:
        menu_item = (
            db.query(models.MenuItem)
            .filter(
                models.MenuItem.id == order.menu_item_id,
                models.MenuItem.restaurant_id == order.restaurant_id,
            )
            .first()
        )
        if not menu_item:
            raise HTTPException(
                status_code=404,
                detail="Menu item not found for this restaurant",
            )

    # ✅ 关键：这里定义 new_order
    new_order = models.Order(
        user_id=current_user.id,
        restaurant_id=order.restaurant_id,
        menu_item_id=order.menu_item_id,
        rider_id=None,
        status="pending",
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    
    return build_order_response(new_order, db)


@app.get("/orders", response_model=list[schemas.OrderResponse])
def get_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == "customer":
        orders = (
            db.query(models.Order)
            .filter(models.Order.user_id == current_user.id)
            .all()
        )
        return [build_order_response(o, db) for o in orders]

    if current_user.role == "rider":
        orders = (
            db.query(models.Order)
            .filter(models.Order.rider_id == current_user.id)
            .all()
        )
        return [build_order_response(o, db) for o in orders]

    raise HTTPException(status_code=403, detail="Not enough permissions")

@app.get("/orders/available", response_model=list[schemas.OrderResponse])
def get_available_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, ["rider"])

    orders = (
        db.query(models.Order)
        .filter(
            models.Order.status == "pending",
            models.Order.rider_id.is_(None)
        )
        .all()
    )

    return [build_order_response(o, db) for o in orders]


@app.put("/orders/{order_id}/assign", response_model=schemas.OrderResponse)
def assign_order(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, ["rider"])

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.rider_id is not None:
        raise HTTPException(status_code=400, detail="Order already assigned")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending orders can be assigned")

    order.rider_id = current_user.id
    order.status = "preparing"

    db.commit()
    db.refresh(order)
    return order

@app.put("/orders/{order_id}/status", response_model=schemas.OrderResponse)
def update_order_status(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, ["rider"])

    order = (
        db.query(models.Order)
        .filter(models.Order.id == order_id, models.Order.rider_id == current_user.id)
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "preparing":
        order.status = "delivering"
    elif order.status == "delivering":
        order.status = "delivered"
    elif order.status == "delivered":
        raise HTTPException(status_code=400, detail="Order already delivered")
    else:
        raise HTTPException(status_code=400, detail="Order status cannot be updated")

    db.commit()
    db.refresh(order)
    return build_order_response(order, db)


@app.get("/owner/orders", response_model=list[schemas.OrderResponse])
def get_owner_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, ["restaurant_owner"])

    owned_restaurants = (
        db.query(models.Restaurant.id)
        .filter(models.Restaurant.owner_id == current_user.id)
        .all()
    )

    restaurant_ids = [r[0] for r in owned_restaurants]

    if not restaurant_ids:
        return []

    orders = (
        db.query(models.Order)
        .filter(models.Order.restaurant_id.in_(restaurant_ids))
        .all()
    )

    return [build_order_response(o, db) for o in orders]

def build_order_response(order, db):
    restaurant = (
        db.query(models.Restaurant)
        .filter(models.Restaurant.id == order.restaurant_id)
        .first()
    )

    menu_item = None
    if order.menu_item_id is not None:
        menu_item = (
            db.query(models.MenuItem)
            .filter(models.MenuItem.id == order.menu_item_id)
            .first()
        )

    return {
        "id": order.id,
        "user_id": order.user_id,
        "restaurant_id": order.restaurant_id,
        "restaurant_name": restaurant.name if restaurant else None,
        "menu_item_id": order.menu_item_id,
        "menu_item_name": menu_item.name if menu_item else None,
        "rider_id": order.rider_id,
        "status": order.status,
    }