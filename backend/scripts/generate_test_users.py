
import asyncio
import sys
import os
import random
import string
import uuid
import argparse

# 프로젝트 루트 디렉토리를 경로에 추가 (backend 모듈 import를 위해)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from backend.core.database.session import AsyncSessionLocal
from backend.features.auth.models import User
from backend.core.auth.providers.credentials import CredentialsAuthProvider

async def generate_users(count: int, output_file: str):
    """
    테스트 유저 생성 및 DB 저장
    """
    generated_users = []
    
    print(f"🚀 Generating {count} test users...")
    
    async with AsyncSessionLocal() as session:
        for i in range(1, count + 1):
            # 1. 이메일 생성 (test{i}@moriai.kr)
            # 이미 존재하는지 체크하는 로직은 생략 (DB Unique constraint에 맡김 or 랜덤성 추가)
            # 여기서는 순차적으로 생성하되, 기존에 있으면 에러날 수 있으니 랜덤 접미사 추가 고려
            # 하지만 요구사항이 단순하므로 순차적으로 시도하되, 에러나면 건너뛰도록 처리
            
            # 요구사항: test(번호)@moriai.kr 
            # 중복 방지를 위해 랜덤 4자리 추가 (옵션) -> 요구사항은 단순히 번호임.
            # 하지만 이미 test1이 있을 수 있으므로... 
            # 일단 단순하게 간다. 충돌나면 스크립트 다시 돌릴 때 offset 필요할 수도 있음.
            # 여기서는 안전하게 1부터 시작하지 않고, 현재 DB max id를 찾는게 정석이지만
            # 간단히 랜덤 숫자를 붙여서 충돌 회피하거나, 그냥 순차적으로 생성함.
            # User wants "test(번호)@moriai.kr". I will follow strictly but catch errors.
            
            email = f"test{i}@moriai.kr"
            
            # 2. 비밀번호 생성 (8자리 랜덤 숫자)
            password = ''.join(random.choices(string.digits, k=8))
            
            # 3. 비밀번호 해싱
            hashed_password = CredentialsAuthProvider.hash_password(password)
            
            # 4. User 객체 생성
            new_user = User(
                email=email,
                password_hash=hashed_password,
                is_active=True,
                oauth_provider=None,
                oauth_id=None
            )
            
            try:
                session.add(new_user)
                await session.flush() # ID 생성을 위해 flush
                # await session.commit() # 개별 커밋 or 일괄 커밋? 일괄이 빠름.
                
                generated_users.append((email, password))
                print(f"   ✓ Added: {email}")
                
            except Exception as e:
                print(f"   ⚠ Failed to add {email}: {e}")
                await session.rollback()
                continue
        
        try:
            await session.commit()
            print("✓ Database commit successful")
        except Exception as e:
            print(f"⚠ Database commit failed: {e}")
            await session.rollback()
            return

    # 5. 파일 출력
    with open(output_file, 'w') as f:
        for email, pwd in generated_users:
            f.write(f"id : {email}\npassword : {pwd}\n")
            
    print(f"\n✨ Successfully generated {len(generated_users)} users.")
    print(f"📁 Credentials saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate test users for MoriAI")
    parser.add_argument("count", type=int, help="Number of users to generate")
    parser.add_argument("--output", type=str, default="generated_users.txt", help="Output file path")
    
    args = parser.parse_args()
    
    if args.count < 1:
        print("Error: Count must be at least 1")
        sys.exit(1)
        
    try:
        asyncio.run(generate_users(args.count, args.output))
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
    except Exception as e:
        print(f"\nMatches Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
