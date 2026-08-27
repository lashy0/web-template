# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "cryptography>=46.0.0,<47.0.0",
# ]
# ///

from cryptography.fernet import Fernet  # noqa: I001


print(Fernet.generate_key().decode())  # noqa: T201
