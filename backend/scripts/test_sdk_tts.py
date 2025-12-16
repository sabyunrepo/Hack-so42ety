#!/usr/bin/env python3
"""
ElevenLabs SDK 기반 TTS Provider 테스트 스크립트

테스트 항목:
1. 단일 알파벳 문자 → eleven_flash_v2 + pronunciation dictionary
2. 일반 단어 → eleven_v3 (또는 default model)
3. Voice 목록 조회
4. 오류 처리
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.infrastructure.ai.providers.elevenlabs_tts import ElevenLabsTTSProvider
from backend.core.config import settings


async def test_single_character_tts():
    """단일 알파벳 문자 테스트 (eleven_flash_v2 + pronunciation dict)"""
    print("\n" + "=" * 60)
    print("테스트 1: 단일 알파벳 문자 'G' TTS 생성")
    print("=" * 60)

    try:
        provider = ElevenLabsTTSProvider()

        # Test single character
        audio_bytes = await provider.text_to_speech(
            text="G",
            voice_id=settings.tts_default_voice_id,
        )

        print(f"✅ 성공: {len(audio_bytes)} bytes 생성")
        print(f"   예상 모델: eleven_flash_v2")
        print(f"   예상 발음 사전: 적용됨 (Uf6eDFq1RYkhUqTogmVc)")

        # Save to file
        output_path = project_root / "test_G.mp3"
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        print(f"   저장 위치: {output_path}")

        return True

    except Exception as e:
        print(f"❌ 실패: {str(e)}")
        return False


async def test_word_tts():
    """일반 단어 테스트 (default model, no pronunciation dict)"""
    print("\n" + "=" * 60)
    print("테스트 2: 일반 단어 'Hello' TTS 생성")
    print("=" * 60)

    try:
        provider = ElevenLabsTTSProvider()

        # Test word
        audio_bytes = await provider.text_to_speech(
            text="Hello",
            voice_id=settings.tts_default_voice_id,
        )

        print(f"✅ 성공: {len(audio_bytes)} bytes 생성")
        print(f"   예상 모델: {settings.tts_default_model_id}")
        print(f"   예상 발음 사전: 적용 안됨")

        # Save to file
        output_path = project_root / "test_Hello.mp3"
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        print(f"   저장 위치: {output_path}")

        return True

    except Exception as e:
        print(f"❌ 실패: {str(e)}")
        return False


async def test_lowercase_character():
    """소문자 알파벳 테스트"""
    print("\n" + "=" * 60)
    print("테스트 3: 소문자 알파벳 'a' TTS 생성")
    print("=" * 60)

    try:
        provider = ElevenLabsTTSProvider()

        # Test lowercase
        audio_bytes = await provider.text_to_speech(
            text="a",
            voice_id=settings.tts_default_voice_id,
        )

        print(f"✅ 성공: {len(audio_bytes)} bytes 생성")
        print(f"   예상 모델: eleven_flash_v2")
        print(f"   예상 발음 사전: 적용됨 (소문자 'a' = EY1)")

        # Save to file
        output_path = project_root / "test_a.mp3"
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        print(f"   저장 위치: {output_path}")

        return True

    except Exception as e:
        print(f"❌ 실패: {str(e)}")
        return False


async def test_get_voices():
    """Voice 목록 조회 테스트"""
    print("\n" + "=" * 60)
    print("테스트 4: 사용 가능한 Voice 목록 조회")
    print("=" * 60)

    try:
        provider = ElevenLabsTTSProvider()

        voices = await provider.get_available_voices()

        print(f"✅ 성공: {len(voices)}개 voice 발견")
        print(f"\n처음 5개 voice:")
        for voice in voices[:5]:
            print(f"   - {voice['name']} ({voice['voice_id']})")
            print(f"     Language: {voice['language']}, Category: {voice['category']}")

        return True

    except Exception as e:
        print(f"❌ 실패: {str(e)}")
        return False


async def test_configuration():
    """설정 확인 테스트"""
    print("\n" + "=" * 60)
    print("설정 확인")
    print("=" * 60)

    print(f"✅ ElevenLabs API Key: {'설정됨' if settings.elevenlabs_api_key else '❌ 미설정'}")
    print(f"✅ Default Voice ID: {settings.tts_default_voice_id}")
    print(f"✅ Default Model ID: {settings.tts_default_model_id}")
    print(f"✅ Pronunciation Dictionary ID: {settings.pronunciation_dictionary_id or '❌ 미설정'}")
    print(f"✅ Pronunciation Version ID: {settings.pronunciation_version_id or '❌ 미설정'}")


async def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("🧪 ElevenLabs SDK TTS Provider 통합 테스트")
    print("=" * 60)

    # Configuration check
    await test_configuration()

    # Run all tests
    results = []
    results.append(("단일 대문자 'G'", await test_single_character_tts()))
    results.append(("일반 단어 'Hello'", await test_word_tts()))
    results.append(("단일 소문자 'a'", await test_lowercase_character()))
    results.append(("Voice 목록 조회", await test_get_voices()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 모든 테스트 통과!")
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패")


if __name__ == "__main__":
    asyncio.run(main())
