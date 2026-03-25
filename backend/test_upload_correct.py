import httpx
import asyncio

async def run_test():
    async with httpx.AsyncClient() as client:
        # We need a user ID. Let's query one via httpx or just create one with correct fields
        # Just create one.
        res = await client.post("http://localhost:8000/onboard", json={
            "phone": "+9999999999",
            "email": "test2@test.com",
            "name": "Test User",
            "initial_cash_balance": 1000.0,
            "monthly_salary": 5000.0,
            "assets": []
        })
        if res.status_code == 200:
            user_id = res.json()['user']['id']
        else:
            print(res.text)
            return

        with open(r'd:\SAI\Projects\cfm\receipt.png', 'rb') as f:
            files = {'file': ('receipt.png', f, 'image/png')}
            data = {'user_id': user_id}
            
            res2 = await client.post("http://localhost:8000/upload-receipt", data=data, files=files)
            print(res2.status_code)
            print(res2.text)

if __name__ == "__main__":
    asyncio.run(run_test())
