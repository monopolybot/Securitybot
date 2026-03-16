from PIL import Image
import hashlib

def get_image_hash(image_bytes):
    try:
        # تحويل الصورة إلى بصمة رقمية سريعة جداً
        img = Image.open(image_bytes)
        img = img.resize((10, 10), Image.Resampling.LANCZOS).convert("L")
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join(['1' if p > avg else '0' for p in pixels])
        hex_hash = hex(int(bits, 2))[2:]
        return hex_hash
    except:
        return None
