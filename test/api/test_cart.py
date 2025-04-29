from src.api.carts import create_cart, set_item_quantity, checkout, Customer, CartItem, CartCheckout, search_orders

def test_create_cart() -> None:
    # Test creating a new cart
    customer = Customer(
        customer_id="123",
        customer_name="Test Customer",
        character_class="Warrior",
        level=1
    )
    
    response = create_cart(customer)
    assert response.cart_id > 0

def test_add_item_to_cart() -> None:
    # First create a cart
    customer = Customer(
        customer_id="124",
        customer_name="Test Customer 2",
        character_class="Mage",
        level=2
    )
    cart = create_cart(customer)
    
    # Add item to cart
    cart_item = CartItem(quantity=2)
    set_item_quantity(cart.cart_id, "RED_POTIONS_0", cart_item)

def test_add_item_to_nonexistent_cart() -> None:
    # Try to add item to nonexistent cart
    cart_item = CartItem(quantity=1)
    try:
        set_item_quantity(999999, "RED_POTIONS_0", cart_item)
        assert False, "Should have raised HTTPException"
    except Exception as e:
        assert "Cart not found" in str(e)

def test_checkout_cart() -> None:
    # Create cart
    customer = Customer(
        customer_id="125",
        customer_name="Test Customer 3",
        character_class="Rogue",
        level=3
    )
    cart = create_cart(customer)
    
    # Add items
    cart_item = CartItem(quantity=3)
    set_item_quantity(cart.cart_id, "RED_POTIONS_0", cart_item)
    
    # Checkout
    checkout_request = CartCheckout(payment="gold")
    response = checkout(cart.cart_id, checkout_request)
    
    assert response.total_potions_bought == 3
    assert response.total_gold_paid == 150  # 3 potions * 50 gold each

def test_checkout_empty_cart() -> None:
    # Create cart
    customer = Customer(
        customer_id="126",
        customer_name="Test Customer 4",
        character_class="Cleric",
        level=4
    )
    cart = create_cart(customer)
    
    # Try to checkout empty cart
    checkout_request = CartCheckout(payment="gold")
    try:
        checkout(cart.cart_id, checkout_request)
        assert False, "Should have raised HTTPException"
    except Exception as e:
        assert "Cart is empty" in str(e)

def test_checkout_nonexistent_cart() -> None:
    # Try to checkout nonexistent cart
    checkout_request = CartCheckout(payment="gold")
    try:
        checkout(999999, checkout_request)
        assert False, "Should have raised HTTPException"
    except Exception as e:
        assert "Cart not found" in str(e)

def test_search_orders() -> None:
    # Create a cart with items and check it out
    customer = Customer(
        customer_id="127",
        customer_name="Test Customer 5",
        character_class="Wizard",
        level=5
    )
    cart = create_cart(customer)
    
    # Add items
    cart_item = CartItem(quantity=2)
    set_item_quantity(cart.cart_id, "RED_POTIONS_0", cart_item)
    
    # Checkout
    checkout_request = CartCheckout(payment="gold")
    checkout(cart.cart_id, checkout_request)
    
    # Test search by customer name
    response = search_orders(customer_name="Test Customer 5")
    assert len(response.results) > 0
    assert response.results[0].customer_name == "Test Customer 5"
    assert response.results[0].item_sku == "RED_POTIONS_0"
    assert response.results[0].line_item_total == 100  # 2 potions * 50 gold