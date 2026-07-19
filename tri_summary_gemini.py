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
        print("💡 요약 모듈 구동에 필요한 라이브러리를 설치합니다:", installed)
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
    진행 중인 요약 요청을 취소(중단)합니다.
    """
    if task_id in active_sessions:
        print(f"🛑 [작업 중단] Gemini 요약 task_id: {task_id} 요청을 중단합니다.")
        try:
            active_sessions[task_id].close()
        except Exception:
            pass
        del active_sessions[task_id]
        return True
    return False

def get_gemini_api_key():
    """
    1순위: 환경변수 'GEMINI_API_KEY' 조회
    2순위: 프로젝트 폴더 내 'gemini_key.txt' 파일 조회
    """
    # 1. 환경변수 조회
    key = os.environ.get("GEMINI_API_KEY")
    if key and key.strip():
        return key.strip()
    
    # 2. gemini_key.txt 파일 조회
    key_filepath = "gemini_key.txt"
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
# 3. Gemini API 요약 구동 함수
# ----------------------------------------------------------------------
def summarize_text(text, task_id=None, api_key=None):
    """
    Google Gemini 1.5 Flash API를 활용해 단일 셀 한국어 번역문을 요약합니다.
    """
    if not text or not text.strip():
        return ""

    if not api_key or not api_key.strip():
        api_key = get_gemini_api_key()

    if api_key:
        api_key = api_key.strip()
        if api_key.lower().startswith("key="):
            api_key = api_key[4:].strip()

    if not api_key:
        raise Exception(
            "Gemini API Key를 찾을 수 없습니다.\n"
            "사용 방법:\n"
            "1. 화면의 'Gemini Key 입력' 상자에 키를 입력합니다.\n"
            "2. 또는 환경 변수 'GEMINI_API_KEY' 혹은 프로젝트 내 'gemini_key.txt' 파일을 생성하여 키를 등록해 주세요."
        )

    # Gemini 3.5 Flash API Endpoint (x-goog-api-key 헤더 인증 방식을 도입하여 AQ. 시작 키 호환성 보장)
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    system_instruction = (
        "You are a professional editor. "
        "Summarize the input Korean text strictly in Korean in a clean fact-sheet style (개조식), adhering to the few-shot examples below:\n\n"
        "Rules:\n"
        "1. Style: Focus on core nouns and concise phrasing. Do NOT write conversational intros, headers, tags (like '요약:', '제목:'), or keywords.\n"
        "2. For Entity/Subject Description: Start with the subject followed by a colon ':', then list key facts separated by periods '.' (e.g., Subject: Fact 1. Fact 2.).\n"
        "3. For Concept/Process Explanation: Summarize the core message using short noun-ending style (~함, ~음) and list examples or details in parentheses ' (예: Example 1, Example 2 등)'.\n\n"
        "--- Example 1 ---\n"
        "Input Text:\n"
        "미카엘라 말버그(Michaela Mahlberg)는 영국 버밍엄 대학교의 코퍼스 언어학 교수입니다. 그녀는 『International Journal of Corpus Linguistics』의 편집장이며, 『Corpus and Discourse』(블룸즈버리) 서적 시리즈의 공동 편집자입니다. 그녀는 웹 애플리케이션 CLiC의 개발을 주도해 왔으며, 이 애플리케이션은 현재까지 전 세계 100여 개국에서 사용되고 있다.\n\n"
        "Wrong Summary (Do NOT do this):\n"
        "영국 버밍엄 대학교 코퍼스 언어학 교수인 미카엘라 말버그의 학술지 편집 및 도서 공동 편집 등의 주요 경력을 소개함.\n"
        "- 그녀가 개발을 주도하여 전 세계 100여 개국에서 활용되고 있는 웹 애플리케이션 CLiC에 대해 기술함.\n\n"
        "Correct Summary Example 1:\n"
        "미카엘라 말버그: 영국 버밍엄 대학교의 코퍼스 언어학 교수. 『International Journal of Corpus Linguistics』 편집장, 『Corpus and Discourse』(블룸즈버리) 서적 시리즈 of 공동 편집자. 웹 애플리케이션 CLiC의 개발 주도.\n\n"
        "--- Example 2 ---\n"
        "Input Text:\n"
        "단어의 패턴과 텍스트 유형 간의 관계는 콘코던스 표본을 다루는 코퍼스 연구뿐만 아니라, 단어 출현 빈도의 분포를 분석하거나 텍스트 간 특정 현상의 빈도를 비교하는 다른 정량적 방법에도 적용됩니다. 예를 들어, 코퍼스 언어학자들은 진행형 형태의 빈도가 시간의 흐름에 따라 어떻게 변화해 왔는지, 혹은 남성과 여성이 서로 다른 유형의 모호성 표현을 사용하는지 여부에 관심을 가질 수 있다.\n\n"
        "Correct Summary Example 2:\n"
        "단어의 패턴과 텍스트 유형 간의 관계는 코퍼스 연구 및 다른 정량적 방법에도 적용됨.(예: 진행형 형태의 통시적 빈도 변화, 성별에 따른 모호성 표현 차이 여부 등)"
    )

    # systemInstruction 필드를 JSON의 루트 레벨에 올바르게 분리 전송하여 모델이 규칙을 정확하게 수행하도록 유도
    payload = {
        "contents": [{
            "parts": [
                {"text": f"요약할 한국어 텍스트:\n{text}"}
            ]
        }],
        "systemInstruction": {
            "parts": [
                {"text": system_instruction}
            ]
        },
        "generationConfig": {
            "temperature": 0.2
        }
    }

    # 동적 취소를 위해 개별 요청 전용 세션 생성
    req_session = requests.Session()
    if task_id:
        active_sessions[task_id] = req_session

    max_retries = 3
    last_error = None
    summary = ""
    try:
        for attempt in range(1, max_retries + 1):
            try:
                response = req_session.post(url, headers=headers, json=payload, timeout=30)
                
                # 429 Too Many Requests (속도 제한) 대응
                if response.status_code == 429:
                    print(f"⚠️ Gemini API 속도 제한(429) 감지. {attempt}/{max_retries} 재시도 대기...")
                    if attempt < max_retries:
                        time.sleep(5 * attempt)  # 5초, 10초 대기 후 루프 재시도
                        continue
                
                response.raise_for_status()
                
                result = response.json()
                summary = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                break
            except Exception as e:
                if task_id and task_id not in active_sessions:
                    raise Exception("Task cancelled by user")
                
                last_error = e
                print(f"⚠️ Gemini API 요약 시도 {attempt}/{max_retries} 실패: {e}")
                if attempt < max_retries:
                    time.sleep(3 * attempt)
                else:
                    print("❌ Gemini API 요약 모든 재시도 실패.")
                    raise last_error
    finally:
        if task_id and task_id in active_sessions:
            del active_sessions[task_id]

    return summary
