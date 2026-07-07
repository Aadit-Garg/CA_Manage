from py_vapid import Vapid
from py_vapid.utils import b64urlencode
import os

vapid = Vapid()
vapid.generate_keys()
private_key_b64 = b64urlencode(vapid.private_key.private_numbers().private_value.to_bytes(32, 'big'))
# The public key point needs to be in uncompressed format (65 bytes, starting with 0x04)
# We can use cryptography to get it
from cryptography.hazmat.primitives import serialization

public_bytes = vapid.public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)
public_key_b64 = b64urlencode(public_bytes)

print(f"VAPID_PRIVATE_KEY={private_key_b64}")
print(f"VAPID_PUBLIC_KEY={public_key_b64}")

with open('.env', 'a') as f:
    f.write(f"\n# Web Push VAPID Keys\n")
    f.write(f"VAPID_PRIVATE_KEY={private_key_b64}\n")
    f.write(f"VAPID_PUBLIC_KEY={public_key_b64}\n")
    f.write(f"VAPID_CLAIM_EMAIL=mailto:admin@camanage.com\n")
