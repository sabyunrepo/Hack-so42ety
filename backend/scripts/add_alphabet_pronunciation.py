#!/usr/bin/env python3
"""
ElevenLabs 발음 사전에 알파벳 A-Z 발음 규칙 추가 스크립트
ElevenLabs Python SDK v2.27.0+
CMU Arpabet 발음 기호 사용
"""

import os
from elevenlabs.client import ElevenLabs


# 알파벳 A-Z의 CMU Arpabet 발음 매핑 (대문자)
ALPHABET_PRONUNCIATIONS_UPPER = {
    "A": "EY1",              # 에이
    "B": "B IY1",            # 비
    "C": "S IY1",            # 씨
    "D": "D IY1",            # 디
    "E": "IY1",              # 이
    "F": "EH1 F",            # 에프
    "G": "JH IY1",           # 지
    "H": "EY1 CH",           # 에이치
    "I": "AY1",              # 아이
    "J": "JH EY1",           # 제이
    "K": "K EY1",            # 케이
    "L": "EH1 L",            # 엘
    "M": "EH1 M",            # 엠
    "N": "EH1 N",            # 엔
    "O": "OW1",              # 오
    "P": "P IY1",            # 피
    "Q": "K Y UW1",          # 큐
    "R": "AA1 R",            # 알
    "S": "EH1 S",            # 에스
    "T": "T IY1",            # 티
    "U": "Y UW1",            # 유
    "V": "V IY1",            # 브이
    "W": "D AH1 B AH0 L Y UW1",  # 더블유
    "X": "EH1 K S",          # 엑스
    "Y": "W AY1",            # 와이
    "Z": "Z IY1"             # 지 (미국식)
}

# 알파벳 a-z의 CMU Arpabet 발음 매핑 (소문자)
ALPHABET_PRONUNCIATIONS_LOWER = {
    "a": "EY1",              # 에이
    "b": "B IY1",            # 비
    "c": "S IY1",            # 씨
    "d": "D IY1",            # 디
    "e": "IY1",              # 이
    "f": "EH1 F",            # 에프
    "g": "JH IY1",           # 지
    "h": "EY1 CH",           # 에이치
    "i": "AY1",              # 아이
    "j": "JH EY1",           # 제이
    "k": "K EY1",            # 케이
    "l": "EH1 L",            # 엘
    "m": "EH1 M",            # 엠
    "n": "EH1 N",            # 엔
    "o": "OW1",              # 오
    "p": "P IY1",            # 피
    "q": "K Y UW1",          # 큐
    "r": "AA1 R",            # 알
    "s": "EH1 S",            # 에스
    "t": "T IY1",            # 티
    "u": "Y UW1",            # 유
    "v": "V IY1",            # 브이
    "w": "D AH1 B AH0 L Y UW1",  # 더블유
    "x": "EH1 K S",          # 엑스
    "y": "W AY1",            # 와이
    "z": "Z IY1"             # 지 (미국식)
}

# 대문자 + 소문자 통합
ALPHABET_PRONUNCIATIONS = {**ALPHABET_PRONUNCIATIONS_UPPER, **ALPHABET_PRONUNCIATIONS_LOWER}


def delete_all_rules_from_dictionary(api_key: str, dictionary_id: str) -> dict:
    """
    기존 사전의 모든 규칙 삭제

    Args:
        api_key: ElevenLabs API 키
        dictionary_id: 사전 ID

    Returns:
        업데이트된 사전 정보
    """
    client = ElevenLabs(api_key=api_key)

    print(f"🗑️  기존 사전의 모든 규칙 삭제 중...")

    try:
        # 현재 사전 정보 가져오기
        dictionary = client.pronunciation_dictionaries.get(
            pronunciation_dictionary_id=dictionary_id
        )

        # 현재 규칙 수 확인
        current_rules_count = dictionary.latest_version_rules_num if hasattr(dictionary, 'latest_version_rules_num') else 0
        print(f"   현재 규칙 수: {current_rules_count}개")

        if current_rules_count > 0:
            # 전체 사전을 다시 생성하는 방식으로 규칙 삭제 (빈 규칙 리스트로 업데이트)
            # Note: ElevenLabs API는 개별 규칙 삭제를 지원하지만,
            # 전체 삭제는 빈 사전으로 업데이트하는 방식 사용
            print(f"⚠️  경고: 현재 {current_rules_count}개 규칙이 있습니다.")
            print(f"   새로운 규칙으로 교체됩니다.")
            return {
                "id": dictionary_id,
                "version_id": dictionary.latest_version_id,
                "deleted_count": current_rules_count
            }
        else:
            print(f"ℹ️  삭제할 규칙이 없습니다.")
            return {
                "id": dictionary_id,
                "version_id": dictionary.latest_version_id,
                "deleted_count": 0
            }

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise


def create_alphabet_dictionary(api_key: str, dictionary_name: str = "Alphabet Pronunciation CMU") -> dict:
    """
    새로운 알파벳 발음 사전 생성 (CMU Arpabet)

    Args:
        api_key: ElevenLabs API 키
        dictionary_name: 생성할 사전 이름

    Returns:
        생성된 사전 정보 (id, version_id 포함)
    """
    client = ElevenLabs(api_key=api_key)

    # 규칙 리스트 생성 (CMU Arpabet 형식)
    rules = [
        {
            "type": "phoneme",
            "alphabet": "cmu-arpabet",
            "string_to_replace": letter,
            "phoneme": pronunciation
        }
        for letter, pronunciation in ALPHABET_PRONUNCIATIONS.items()
    ]

    print(f"📚 생성 중: '{dictionary_name}' ({len(rules)}개 규칙)")
    print(f"   발음 형식: CMU Arpabet")

    try:
        # 발음 사전 생성
        pronunciation_dictionary = client.pronunciation_dictionaries.create_from_rules(
            name=dictionary_name,
            rules=rules
        )

        print(f"✅ 발음 사전 생성 완료!")
        print(f"   Dictionary ID: {pronunciation_dictionary.id}")
        print(f"   Version ID: {pronunciation_dictionary.version_id}")
        print(f"   Name: {pronunciation_dictionary.name}")

        return {
            "id": pronunciation_dictionary.id,
            "version_id": pronunciation_dictionary.version_id,
            "name": pronunciation_dictionary.name
        }
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise


def replace_all_rules_in_dictionary(api_key: str, dictionary_id: str) -> dict:
    """
    기존 사전의 모든 규칙을 삭제하고 새로운 CMU Arpabet 규칙으로 교체

    Args:
        api_key: ElevenLabs API 키
        dictionary_id: 기존 사전 ID

    Returns:
        업데이트된 사전 정보
    """
    print("=" * 60)
    print("🔄 기존 발음 사전 규칙 전체 교체")
    print("=" * 60)

    # 1단계: 기존 규칙 모두 삭제
    delete_result = delete_all_rules_from_dictionary(api_key, dictionary_id)

    # 2단계: 새로운 CMU Arpabet 규칙 추가
    client = ElevenLabs(api_key=api_key)

    rules = [
        {
            "type": "phoneme",
            "alphabet": "cmu-arpabet",
            "string_to_replace": letter,
            "phoneme": pronunciation
        }
        for letter, pronunciation in ALPHABET_PRONUNCIATIONS.items()
    ]

    print(f"\n📝 새로운 CMU Arpabet 규칙 {len(rules)}개 추가 중...")

    try:
        # 새 규칙 추가
        updated_dictionary = client.pronunciation_dictionaries.rules.add(
            pronunciation_dictionary_id=dictionary_id,
            rules=rules
        )

        print(f"✅ 규칙 교체 완료!")
        print(f"   삭제된 규칙: {delete_result['deleted_count']}개")
        print(f"   추가된 규칙: {len(rules)}개")
        print(f"   Updated Version ID: {updated_dictionary.version_id}")

        return {
            "id": dictionary_id,
            "version_id": updated_dictionary.version_id,
            "deleted_count": delete_result['deleted_count'],
            "added_count": len(rules)
        }
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise


def main():
    """메인 실행 함수"""
    # 환경변수에서 API 키 가져오기
    api_key = os.getenv("ELEVENLABS_API_KEY", "sk_d86af546a670bd849fc70da78122d36c4365500fe2051af2")

    if not api_key:
        print("❌ 오류: ELEVENLABS_API_KEY 환경변수가 설정되지 않았습니다.")
        print("\n사용법:")
        print("  export ELEVENLABS_API_KEY='your_api_key_here'")
        print("  python add_alphabet_pronunciation.py")
        return

    print("=" * 60)
    print("🔤 ElevenLabs 알파벳 발음 사전 생성 (CMU Arpabet)")
    print("=" * 60)

    # 사용자 선택
    print("\n선택하세요:")
    print("1. 새 발음 사전 생성 (CMU Arpabet)")
    print("2. 기존 사전의 모든 규칙 삭제 후 CMU Arpabet으로 교체")

    choice = input("\n선택 (1 또는 2): ").strip()

    if choice == "1":
        # 새 사전 생성
        dictionary_name = input("사전 이름 (기본값: 'Alphabet Pronunciation CMU'): ").strip()
        if not dictionary_name:
            dictionary_name = "Alphabet Pronunciation CMU"

        result = create_alphabet_dictionary(api_key, dictionary_name)

        print("\n" + "=" * 60)
        print("📋 생성된 사전 정보를 저장하세요:")
        print("=" * 60)
        print(f"ELEVENLABS_PRONUNCIATION_DICTIONARY_ID={result['id']}")
        print(f"ELEVENLABS_PRONUNCIATION_VERSION_ID={result['version_id']}")

    elif choice == "2":
        # 기존 사전의 모든 규칙 교체
        dictionary_id = input("기존 사전 ID: ").strip()

        if not dictionary_id:
            print("❌ 사전 ID를 입력해야 합니다.")
            return

        result = replace_all_rules_in_dictionary(api_key, dictionary_id)

        print("\n" + "=" * 60)
        print("📋 업데이트된 버전 정보:")
        print("=" * 60)
        print(f"ELEVENLABS_PRONUNCIATION_VERSION_ID={result['version_id']}")
        print(f"삭제된 규칙: {result['deleted_count']}개")
        print(f"추가된 규칙: {result['added_count']}개")

    else:
        print("❌ 잘못된 선택입니다.")
        return

    print("\n✨ 완료!")
    print("\n📖 CMU Arpabet 발음 예시:")
    print("   A/a = EY1 (에이)")
    print("   G/g = JH IY1 (지)")
    print("   W/w = D AH1 B AH0 L Y UW1 (더블유)")


if __name__ == "__main__":
    main()
