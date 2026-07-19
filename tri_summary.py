import os
import sys
import subprocess
import time
import re

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
# 2. 글로벌 설정 및 커넥션 세션 최적화
# ----------------------------------------------------------------------
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
MODEL_NAME = "hf.co/lmstudio-community/gemma-4-E4B-it-GGUF:Q4_K_M"

session = requests.Session()
summary_count = 0  # 셀 요약 누적 카운터

# ----------------------------------------------------------------------
# 3. 메모리 관리 로직 (VRAM 언로드)
# ----------------------------------------------------------------------
def unload_ollama_model():
    """
    Ollama 모델과 KV 캐시를 GPU 메모리(VRAM)에서 언로드하여 누적된 부담을 해제합니다.
    Ollama 엔진 자체의 종료나 모델 크래시를 방지하기 위해 예외를 완벽히 감싸서 격리 처리합니다.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": "",
        "keep_alive": 0,
        "stream": False
    }
    try:
        # 빈 generate 요청에 keep_alive = 0 을 전달하여 즉각 메모리 해제를 요청
        # 타임아웃을 안전하게 10초로 지정하여 통신 중단을 막음
        session.post(OLLAMA_GENERATE_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ VRAM 메모리 정리 중 예외 발생 (무시 가능): {e}")

# ----------------------------------------------------------------------
# 4. 작업 중단 및 세션 관리 로직
# ----------------------------------------------------------------------
active_sessions = {}

def cancel_request(task_id):
    if task_id in active_sessions:
        print(f"🛑 [작업 중단] 요약 task_id: {task_id} 요청을 중단합니다.")
        try:
            active_sessions[task_id].close()
        except Exception:
            pass
        del active_sessions[task_id]
        return True
    return False

def clean_thinking_process(text):
    """
    로컬 LLM이 생성한 응답에서 사고 과정(Thinking Process) 태그를 제거합니다.
    """
    if not text:
        return ""
    # <|channel>thought ... <channel|> 또는 </channel|> 패턴 제거 (Gemma4 IT 등)
    text = re.sub(r'<\|channel>thought.*?</?channel\|>', '', text, flags=re.DOTALL)
    # <think> ... </think> 패턴 제거 (DeepSeek R1 등)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return text.strip()

# ----------------------------------------------------------------------
# 5. 단일 텍스트 요약 함수
# ----------------------------------------------------------------------
def summarize_text(text, task_id=None):
    """
    단일 셀 텍스트를 Ollama Gemma4 모델을 사용해 1~3문장 이내로 한국어 해라체로 요약합니다.
    """
    global summary_count, session

    system_prompt = (
        "You are a professional academic summarizer. "
        "Your task is to summarize the input Korean text in a clean fact-sheet style (개조식) strictly adhering to the few-shot examples below:\n\n"
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
        "미카엘라 말버그: 영국 버밍엄 대학교의 코퍼스 언어학 교수. 『International Journal of Corpus Linguistics』 편집장, 『Corpus and Discourse』(블룸즈버리) 서적 시리즈의 공동 편집자. 웹 애플리케이션 CLiC의 개발 주도.\n\n"
        "--- Example 2 ---\n"
        "Input Text:\n"
        "단어의 패턴과 텍스트 유형 간의 관계는 콘코던스 표본을 다루는 코퍼스 연구뿐만 아니라, 단어 출현 빈도의 분포를 분석하거나 텍스트 간 특정 현상의 빈도를 비교하는 다른 정량적 방법에도 적용됩니다. 예를 들어, 코퍼스 언어학자들은 진행형 형태의 빈도가 시간의 흐름에 따라 어떻게 변화해 왔는지, 혹은 남성과 여성이 서로 다른 유형의 모호성 표현을 사용하는지 여부에 관심을 가질 수 있다.\n\n"
        "Correct Summary Example 2:\n"
        "단어의 패턴과 텍스트 유형 간의 관계는 코퍼스 연구 및 다른 정량적 방법에도 적용됨.(예: 진행형 형태의 통시적 빈도 변화, 성별에 따른 모호성 표현 차이 여부 등)"
    )

    prompt = f"<start_of_turn>system\n{system_prompt}<end_of_turn>\n<start_of_turn>user\n{text}<end_of_turn>\n<start_of_turn>model\n"

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "options": {
            "temperature": 0.3,
            "num_ctx": 4096,
            "num_predict": 4096
        },
        "stream": False
    }

    # 개별 요청 세션 생성 (취소 가능성을 위해)
    req_session = requests.Session()
    if task_id:
        active_sessions[task_id] = req_session

    max_retries = 3
    last_error = None
    summarized = ""
    try:
        for attempt in range(1, max_retries + 1):
            try:
                # 모델이 언로드된 상태일 수 있으므로 타임아웃을 120초로 넉넉하게 지정합니다.
                response = req_session.post(OLLAMA_GENERATE_URL, json=payload, timeout=120)
                response.raise_for_status()
                result = response.json()
                summarized = result["response"].strip()
                break
            except Exception as e:
                # 사용자가 요청을 중단(close) 시켜서 ConnectionError가 난 경우에는 재시도 없이 즉시 중단합니다.
                if task_id and task_id not in active_sessions:
                    print(f"🛑 [작업 중단 감지] task_id: {task_id} 재시도를 중단하고 빠져나갑니다.")
                    raise Exception("Task cancelled by user")

                last_error = e
                print(f"⚠️ Ollama API 요약 시도 {attempt}/{max_retries} 실패: {e}")
                if attempt < max_retries:
                    time.sleep(2 * attempt)  # 재시도 간격 점진적 증가
                else:
                    print("❌ 모든 요약 재시도 실패.")
                    raise last_error
    finally:
        if task_id and task_id in active_sessions:
            del active_sessions[task_id]

    # 요약 카운터 증가 및 20회마다 메모리 정리 실행
    summary_count += 1
    if summary_count % 20 == 0:
        print(f"🧹 [메모리 최적화] {summary_count}회 요약 완료. VRAM 모델 언로드 및 세션을 갱신합니다...")
        try:
            unload_ollama_model()
        except Exception:
            pass
        session = requests.Session()

    summarized = clean_thinking_process(summarized)
    return summarized
