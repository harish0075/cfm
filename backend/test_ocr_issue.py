import sys
from PIL import Image
from io import BytesIO

def test_image(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()

    print(f"Read {len(data)} bytes")
    try:
        img = Image.open(BytesIO(data))
        img.verify()
        print('BytesIO Verified!')
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_image(r'd:\SAI\Projects\cfm\receipt.png')
