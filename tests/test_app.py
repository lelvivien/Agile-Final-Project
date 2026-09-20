import base64
import io
import os
import tempfile
import unittest

from app import create_app

PNG_IMAGE_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5W3n0AAAAASUVORK5CYII="
)


class ProductCatalogTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.static_dir = os.path.join(self.temp_dir.name, "static")
        self.upload_dir = os.path.join(self.static_dir, "uploads")
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.db_path,
                "STATIC_FOLDER": self.static_dir,
                "UPLOAD_FOLDER": self.upload_dir,
                "SECRET_KEY": "test",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_catalog_form_is_available(self):
        response = self.client.get("/products/new")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Product image", response.data)
        self.assertIn(b"Description", response.data)
        self.assertIn(b"Category", response.data)
        self.assertIn(b"Price", response.data)

    def test_create_product_displays_it_in_catalog(self):
        response = self.client.post(
            "/products/new",
            data={
                "description": "Travel Mug",
                "category": "Accessories",
                "price": "12.50",
                "image": (io.BytesIO(PNG_IMAGE_BYTES), "mug.png"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Travel Mug", response.data)
        self.assertIn(b"Category: Accessories", response.data)
        self.assertIn(b"Price: $12.50", response.data)
        self.assertIn(b"/static/uploads/", response.data)
        self.assertTrue(os.listdir(self.upload_dir))

    def test_create_product_requires_image(self):
        response = self.client.post(
            "/products/new",
            data={
                "description": "Travel Mug",
                "category": "Accessories",
                "price": "12.50",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Product image is required.", response.data)
        self.assertEqual(os.listdir(self.upload_dir), [])

    def test_create_product_rejects_invalid_price(self):
        response = self.client.post(
            "/products/new",
            data={
                "description": "Travel Mug",
                "category": "Accessories",
                "price": "-1.00",
                "image": (io.BytesIO(PNG_IMAGE_BYTES), "mug.png"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Price must be a non-negative number.", response.data)
        self.assertEqual(os.listdir(self.upload_dir), [])

    def test_create_product_rejects_non_finite_price(self):
        response = self.client.post(
            "/products/new",
            data={
                "description": "Travel Mug",
                "category": "Accessories",
                "price": "NaN",
                "image": (io.BytesIO(PNG_IMAGE_BYTES), "mug.png"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Price must be a non-negative number.", response.data)
        self.assertEqual(os.listdir(self.upload_dir), [])

    def test_create_product_rejects_non_image_upload(self):
        response = self.client.post(
            "/products/new",
            data={
                "description": "Travel Mug",
                "category": "Accessories",
                "price": "12.50",
                "image": (io.BytesIO(b"not an image"), "mug.txt"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Product image must be a GIF, JPEG, PNG, or WebP file.",
            response.data,
        )
        self.assertEqual(os.listdir(self.upload_dir), [])


if __name__ == "__main__":
    unittest.main()
