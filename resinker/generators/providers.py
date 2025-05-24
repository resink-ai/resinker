"""
Custom Faker providers for Resinker.
"""

from faker.providers import BaseProvider
import random


class EcommerceProvider(BaseProvider):
    """Provider for ecommerce-related fake data."""

    product_categories = [
        "Electronics",
        "Clothing",
        "Home & Kitchen",
        "Books",
        "Beauty",
        "Sports",
        "Toys",
        "Automotive",
        "Health",
        "Pet Supplies",
    ]

    product_adjectives = [
        "Premium",
        "Deluxe",
        "Essential",
        "Professional",
        "Ultra",
        "Smart",
        "Portable",
        "Wireless",
        "Digital",
        "Organic",
        "Vintage",
        "Modern",
        "Lightweight",
        "Durable",
        "Advanced",
    ]

    product_types = {
        "Electronics": [
            "Headphones",
            "Smartphone",
            "Laptop",
            "Tablet",
            "Camera",
            "Smartwatch",
            "Speaker",
            "TV",
            "Monitor",
            "Mouse",
            "Keyboard",
        ],
        "Clothing": [
            "T-Shirt",
            "Jeans",
            "Dress",
            "Jacket",
            "Sweater",
            "Socks",
            "Hat",
            "Scarf",
            "Gloves",
            "Shoes",
            "Sneakers",
        ],
        "Home & Kitchen": [
            "Blender",
            "Coffee Maker",
            "Toaster",
            "Microwave",
            "Sofa",
            "Bed",
            "Table",
            "Chair",
            "Lamp",
            "Pillow",
            "Blanket",
        ],
        "Books": [
            "Novel",
            "Cookbook",
            "Biography",
            "Textbook",
            "Guide",
            "History Book",
            "Dictionary",
            "Comic Book",
            "Magazine",
            "Journal",
        ],
        "Beauty": [
            "Lipstick",
            "Foundation",
            "Mascara",
            "Moisturizer",
            "Shampoo",
            "Conditioner",
            "Body Wash",
            "Face Mask",
            "Perfume",
        ],
        "Sports": [
            "Yoga Mat",
            "Dumbbells",
            "Tennis Racket",
            "Basketball",
            "Football",
            "Baseball Glove",
            "Bicycle",
            "Skateboard",
            "Running Shoes",
        ],
        "Toys": [
            "Action Figure",
            "Doll",
            "Board Game",
            "Puzzle",
            "Plush Toy",
            "Remote Control Car",
            "Building Blocks",
            "Art Set",
        ],
        "Automotive": [
            "Car Seat",
            "Windshield Wipers",
            "Floor Mats",
            "Car Charger",
            "Jump Starter",
            "Tool Kit",
            "Air Freshener",
        ],
        "Health": [
            "Vitamins",
            "Supplements",
            "First Aid Kit",
            "Thermometer",
            "Blood Pressure Monitor",
            "Heating Pad",
            "Massager",
        ],
        "Pet Supplies": [
            "Dog Food",
            "Cat Litter",
            "Pet Bed",
            "Pet Toy",
            "Pet Carrier",
            "Leash",
            "Collar",
            "Pet Shampoo",
        ],
    }

    def product_name(self):
        """Generate a random product name."""
        category = self.random_element(self.product_categories)
        adjective = self.random_element(self.product_adjectives)
        product_type = self.random_element(self.product_types[category])

        # Sometimes include the category in the name
        if random.random() < 0.3:
            return f"{adjective} {category} {product_type}"
        else:
            return f"{adjective} {product_type}"
