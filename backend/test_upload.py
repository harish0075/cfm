import asyncio
from sqlalchemy import select
from httpx import AsyncClient
import httpx
from database import async_session
from models.user import User
from main import app

async def test_upload():
    async with async_session() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
    
    if not user:
        print("No user in DB")
        return
    
    user_id = str(user.id)
    print(f"Using user {user_id}")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with open(r'd:\SAI\Projects\cfm\receipt.png', 'rb') as f:
            files = {'file': ('receipt.png', f, 'image/png')}
            data = {'user_id': user_id}
            res = await client.post("/upload-receipt", data=data, files=files)
            print(f"Status: {res.status_code}")
            print(f"Response: {res.text}")

if __name__ == "__main__":
    asyncio.run(test_upload())
