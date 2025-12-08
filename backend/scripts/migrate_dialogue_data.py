"""
데이터 마이그레이션 스크립트
기존 dialogues 테이블의 text_en, text_ko, audio_url 데이터를
dialogue_translations 및 dialogue_audios 테이블로 이전
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import engine, get_db
from backend.domain.models.book import Dialogue, DialogueTranslation, DialogueAudio
from datetime import datetime
import uuid


async def migrate_dialogue_data():
    """
    기존 Dialogue 데이터를 새로운 구조로 마이그레이션
    """
    print("=" * 60)
    print("Dialogue 데이터 마이그레이션 시작")
    print("=" * 60)

    async with engine.begin() as conn:
        # 트랜잭션 시작
        session = AsyncSession(bind=conn, expire_on_commit=False)

        try:
            # 1. 모든 Dialogue 조회
            result = await session.execute(
                select(Dialogue).order_by(Dialogue.created_at)
            )
            dialogues = result.scalars().all()

            total_dialogues = len(dialogues)
            print(f"\n총 {total_dialogues}개의 Dialogue 레코드 발견")

            if total_dialogues == 0:
                print("마이그레이션할 데이터가 없습니다.")
                return

            migrated_count = 0
            translation_count = 0
            audio_count = 0

            # 2. 각 Dialogue 처리
            for idx, dialogue in enumerate(dialogues, 1):
                print(f"\n[{idx}/{total_dialogues}] Dialogue ID: {dialogue.id}")

                # 2.1 영어 번역 이전
                if dialogue.text_en:
                    translation_en = DialogueTranslation(
                        id=uuid.uuid4(),
                        dialogue_id=dialogue.id,
                        language_code="en",
                        text=dialogue.text_en,
                        is_primary=True,  # 영어를 원본 언어로 설정
                        created_at=dialogue.created_at,
                        updated_at=dialogue.updated_at,
                    )
                    session.add(translation_en)
                    translation_count += 1
                    print(f"  ✅ 영어 번역 추가 (is_primary=True)")

                # 2.2 한국어 번역 이전
                if dialogue.text_ko:
                    translation_ko = DialogueTranslation(
                        id=uuid.uuid4(),
                        dialogue_id=dialogue.id,
                        language_code="ko",
                        text=dialogue.text_ko,
                        is_primary=False,
                        created_at=dialogue.created_at,
                        updated_at=dialogue.updated_at,
                    )
                    session.add(translation_ko)
                    translation_count += 1
                    print(f"  ✅ 한국어 번역 추가 (is_primary=False)")

                # 2.3 오디오 URL 이전 (언어 추론)
                if dialogue.audio_url:
                    # 오디오는 원본 언어(영어)로 가정
                    # 기본 voice_id 사용 (ElevenLabs Rachel)
                    audio = DialogueAudio(
                        id=uuid.uuid4(),
                        dialogue_id=dialogue.id,
                        language_code="en",  # 영어 오디오로 가정
                        voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel (기본 음성)
                        audio_url=dialogue.audio_url,
                        duration=None,  # duration 정보 없음
                        created_at=dialogue.created_at,
                        updated_at=dialogue.updated_at,
                    )
                    session.add(audio)
                    audio_count += 1
                    print(f"  ✅ 오디오 추가 (language=en, voice=Rachel)")

                migrated_count += 1

            # 3. 변경사항 커밋
            await session.flush()

            print("\n" + "=" * 60)
            print("마이그레이션 완료 요약")
            print("=" * 60)
            print(f"총 Dialogue 처리: {migrated_count}개")
            print(f"생성된 번역: {translation_count}개")
            print(f"생성된 오디오: {audio_count}개")

            # 4. 기존 컬럼 데이터 삭제 (NULL로 설정)
            print("\n기존 컬럼 데이터 삭제 중...")
            await session.execute(
                update(Dialogue)
                .values(
                    text_en=None,
                    text_ko=None,
                    audio_url=None,
                )
            )
            await session.flush()
            print("✅ 기존 컬럼 데이터 삭제 완료")

            print("\n" + "=" * 60)
            print("✅ 모든 마이그레이션 작업 완료!")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ 에러 발생: {e}")
            await session.rollback()
            raise


async def verify_migration():
    """
    마이그레이션 결과 검증
    """
    print("\n" + "=" * 60)
    print("마이그레이션 검증 중...")
    print("=" * 60)

    async with engine.begin() as conn:
        session = AsyncSession(bind=conn, expire_on_commit=False)

        # Dialogue 수 확인
        dialogue_result = await session.execute(select(Dialogue))
        dialogue_count = len(dialogue_result.scalars().all())

        # Translation 수 확인
        translation_result = await session.execute(select(DialogueTranslation))
        translation_count = len(translation_result.scalars().all())

        # Audio 수 확인
        audio_result = await session.execute(select(DialogueAudio))
        audio_count = len(audio_result.scalars().all())

        print(f"\n📊 최종 통계:")
        print(f"  - Dialogue 레코드: {dialogue_count}개")
        print(f"  - Translation 레코드: {translation_count}개")
        print(f"  - Audio 레코드: {audio_count}개")

        # 기존 컬럼에 데이터가 남아있는지 확인
        remaining_result = await session.execute(
            select(Dialogue).where(
                (Dialogue.text_en.isnot(None)) |
                (Dialogue.text_ko.isnot(None)) |
                (Dialogue.audio_url.isnot(None))
            )
        )
        remaining = len(remaining_result.scalars().all())

        if remaining > 0:
            print(f"\n⚠️  경고: {remaining}개의 Dialogue에 아직 기존 데이터가 남아있습니다!")
        else:
            print(f"\n✅ 검증 완료: 모든 기존 컬럼이 정상적으로 비워졌습니다.")


async def main():
    """메인 실행 함수"""
    try:
        # 마이그레이션 실행
        await migrate_dialogue_data()

        # 결과 검증
        await verify_migration()

    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 데이터베이스 연결 종료
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
