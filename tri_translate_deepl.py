import os
import sys
import subprocess
import time

# ----------------------------------------------------------------------
# 1. 의존성 패키지 자동 설치 및 임포트 로직
# ----------------------------------------------------------------------
def install_dependencies():
    required = {'requests'}
    installed = set()
    
    try:
        import requests
    except ImportError:
        installed.add('requests')
        
    if installed:
        print("💡 번역 모듈 구동에 필요한 라이브러리를 설치합니다:", installed)
        try:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            subprocess.check_call([sys.executable, "-m", "pip", "install", *installed], env=env)
            print("✅ 필수 라이브러리 설치 완료.\n")
        except Exception as e:
            print(f"❌ 패키지 자동 설치 실패: {e}")
            sys.exit(1)

install_dependencies()
import requests

# ----------------------------------------------------------------------
# 2. 글로벌 설정 및 세션 관리
# ----------------------------------------------------------------------
active_sessions = {}

def cancel_request(task_id):
    """
    진행 중인 번역 요청을 취소(중단)합니다.
    """
    if task_id in active_sessions:
        print(f"🛑 [작업 중단] DeepL 번역 task_id: {task_id} 요청을 중단합니다.")
        try:
            active_sessions[task_id].close()
        except Exception:
            pass
        del active_sessions[task_id]
        return True
    return False

def get_deepl_api_key():
    """
    1순위: 환경변수 'DEEPL_API_KEY' 조회
    2순위: 프로젝트 폴더 내 'deepl_key.txt' 파일 조회
    """
    # 1. 환경변수 조회
    key = os.environ.get("DEEPL_API_KEY")
    if key and key.strip():
        return key.strip()
    
    # 2. deepl_key.txt 파일 조회
    key_filepath = "deepl_key.txt"
    if os.path.exists(key_filepath):
        try:
            with open(key_filepath, 'r', encoding='utf-8') as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception:
            pass
            
    return None

# ----------------------------------------------------------------------
# 3. 용어 사전(Glossary) 단순 치환 후처리 함수
# ----------------------------------------------------------------------
def apply_glossary(text, filepath="glossary.txt"):
    """
    glossary.txt 사전 내용을 바탕으로 번역 완료된 한글 텍스트 내의 영문 단어를 치환해 줍니다.
    """
    if not os.path.exists(filepath):
        return text

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    parts = line.split('=', 1)
                    eng = parts[0].strip()
                    kor = parts[1].strip()
                    if eng and kor:
                        # 단순 대소문자 매칭 치환 (문장 내의 영문 용어를 한글 매핑 용어로 후처리 치환)
                        # 예: "Mills" -> "밀스"
                        import re
                        pattern = re.compile(re.escape(eng), re.IGNORECASE)
                        text = pattern.sub(f"{kor}({eng})", text)
    except Exception:
        pass
    return text

# ----------------------------------------------------------------------
# 4. DeepL API 번역 구동 함수
# ----------------------------------------------------------------------
def translate_text(text, task_id=None, api_key=None, unload_on_limit=False):
    """
    DeepL REST API를 활용해 단일 셀 텍스트를 영한 번역합니다.
    """
    if not text or not text.strip():
        return ""

    if not api_key or not api_key.strip():
        api_key = get_deepl_api_key()
    if not api_key:
        raise Exception(
            "DeepL API Key를 찾을 수 없습니다.\n"
            "사용 방법:\n"
            "1. 환경 변수 'DEEPL_API_KEY'에 API 키를 등록합니다.\n"
            "2. 또는 프로젝트 폴더에 'deepl_key.txt' 파일을 만들고 그 안에 API 키를 저장해 주세요."
        )

    # API 키 형식에 따라 무료/유료 URL 동적 전환 (fx로 끝나면 무료 플랜 엔드포인트)
    if api_key.endswith(":fx"):
        url = "https://api-free.deepl.com/v2/translate"
    else:
        url = "https://api.deepl.com/v2/translate"

    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/json"
    }

    # DeepL API 형식 사양 (한 번에 리스트 형태로 보냄)
    payload = {
        "text": [text],
        "target_lang": "KO"
    }

    # 동적 취소를 위해 개별 요청 전용 세션 생성
    req_session = requests.Session()
    if task_id:
        active_sessions[task_id] = req_session

    try:
        response = req_session.post(url, headers=headers, json=payload, timeout=30)
        
        # DeepL 전용 한도 도달 에러 처리
        if response.status_code == 456:
            raise Exception("DeepL API 번역 한도(50만 자)를 초과하였습니다. 무료 플랜 쿼터가 만료되었습니다.")
        
        response.raise_for_status()
        
        result = response.json()
        translated = result["translations"][0]["text"].strip()
        
    except Exception as e:
        # 사용자가 취소하여 세션이 닫힌 경우
        if task_id and task_id not in active_sessions:
            raise Exception("Task cancelled by user")
        
        print(f"❌ DeepL API 번역 오류: {e}")
        raise e
    finally:
        if task_id and task_id in active_sessions:
            del active_sessions[task_id]

    # 용어 사전(Glossary) 후처리 적용
    translated = apply_glossary(translated, "glossary.txt")
    
    return translated
