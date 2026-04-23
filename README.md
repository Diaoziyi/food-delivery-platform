Food Delivery Platform (Backend)

A role-based food delivery backend system simulating a three-sided marketplace including customers, riders, and restaurant owners.
Built with FastAPI, PostgreSQL, Docker, and Alembic, this project demonstrates real-world backend architecture, authentication, and API design.

Features

# Authentication & Users

* User registration with role selection (customer / rider / restaurant_owner)
* Secure login with JWT authentication
* Protected routes using OAuth2


###  Restaurant Management (Owner)

* Claim a restaurant
* Create and manage menu items
* View orders for owned restaurants

---

###  Customer Flow

* Browse restaurants
* View menu items
* Place orders for specific menu items
* View personal order history

---

###  Rider Flow

* View available orders (pending & unassigned)
* Accept orders
* Update delivery status:

  * pending → preparing → delivering → delivered

---

###  Order System

* Orders linked to:

  * User
  * Restaurant
  * Menu Item
  * Rider
* Enriched API responses with:

  * restaurant_name
  * menu_item_name

---

##  Tech Stack

* FastAPI
* PostgreSQL
* SQLAlchemy
* JWT (python-jose)
* passlib (bcrypt)
* Docker & Docker Compose
* Alembic

---

##  Run the Project

```bash
docker compose up --build
```

Then open:

```
http://127.0.0.1:8000/docs
```

---

##  Example Workflow

1. Register users (customer / rider / owner)
2. Owner claims restaurant and creates menu
3. Customer browses menu and places order
4. Rider views available orders and accepts them
5. Rider updates delivery status

---

##  Example Order Response

```json
{
  "id": 4,
  "user_id": 3,
  "restaurant_id": 1,
  "restaurant_name": "Burger House",
  "menu_item_id": 1,
  "menu_item_name": "Classic Burger",
  "rider_id": null,
  "status": "pending"
}
```

---

##  Future Improvements

* Frontend (React / Next.js)
* Payment integration
* Real-time tracking
* Redis caching
* CI/CD pipeline

---

##  Author

Ziyi
