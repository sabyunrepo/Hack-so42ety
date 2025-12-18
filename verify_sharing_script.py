import asyncio
import httpx
import uuid

BASE_URL = "http://localhost:8000/api/v1"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Sign Up User
        email = f"shared_test_{uuid.uuid4()}@example.com"
        password = "password123"
        print(f"Creating user {email}...")
        
        # Determine auth endpoint (signup)
        # Attempt standard path /auth/signup
        resp = await client.post("/auth/signup", json={
            "email": email,
            "password": password,
            "full_name": "Test User",
            "nickname": "Tester"
        })
        
        if resp.status_code != 201 and resp.status_code != 200:
             print(f"Signup failed: {resp.status_code} {resp.text}")
             # Try login if already exists (unlikely with uuid)
             return

        # Login to get token
        resp_login = await client.post("/auth/login/email", data={
            "username": email,
            "password": password
        })
        if resp_login.status_code != 200:
            print(f"Login failed: {resp_login.status_code} {resp_login.text}")
            return
            
        token = resp_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Logged in.")

        # 2. Create Book (Mock or minimal)
        # To avoid complex creation (AI), we might need to rely on existing book if possible,
        # or use the /create endpoint if it's fast enough.
        # But /create triggers AI.
        # Check if there is a 'draft' creation or 'simple' creation?
        # create_storybook endpoint: /storybook/create
        # It calls orchestrator.
        
        # If we cannot create easily via API, this script is limited.
        # BUT, I can insert into DB via docker exec SQL if needed, then use API to test sharing.
        
        # Let's try to create a book. 
        # If it takes too long, we can abort.
        # Actually, let's look for a lightweight way.
        # Maybe use a pre-existing book if any?
        # Or Just insert via SQL command line?
        
        pass

if __name__ == "__main__":
    asyncio.run(main())
