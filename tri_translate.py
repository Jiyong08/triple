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
# 2. 글로벌 설정 및 커넥션 세션 최적화
# ----------------------------------------------------------------------
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
MODEL_NAME = "hf.co/lmstudio-community/gemma-4-E4B-it-GGUF:Q4_K_M"

session = requests.Session()
translation_count = 0  # 셀 번역 누적 카운터

# ----------------------------------------------------------------------
# 3. 용어 사전(Glossary) 관련 로직
# ----------------------------------------------------------------------
def load_glossary(filepath="glossary.txt"):
    """
    glossary.txt 파일을 읽어 용어 사전 딕셔너리를 반환합니다.
    """
    glossary = {}
    if not os.path.exists(filepath):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("# [번역 용어 사전 / Glossary]\n")
                f.write("Stylistics = 스타일리스틱스\n")
                f.write("Feminism = 페미니즘\n")
                f.write("Feminist = 페미니스트\n")
                f.write("Mills = 밀스\n")
        except Exception as e:
            pass
    
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        parts = line.split('=', 1)
                        eng = parts[0].strip()
                        kor = parts[1].strip()
                        if eng and kor:
                            glossary[eng.lower()] = kor
        except Exception as e:
            pass
            
    return glossary

# ----------------------------------------------------------------------
# 4. 메모리 관리 로직 (VRAM 언로드)
# ----------------------------------------------------------------------
def unload_ollama_model():
    """
    Ollama 모델과 KV 캐시를 GPU 메모리(VRAM)에서 언로드하여 누적된 부담을 해제합니다.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": "",
        "keep_alive": 0,
        "stream": False
    }
    try:
        # 빈 generate 요청에 keep_alive = 0 을 전달하여 즉각 메모리 해제를 요청
        response = session.post(OLLAMA_GENERATE_URL, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"⚠️ VRAM 메모리 정리 중 예외 발생 (무시 가능): {e}")

# ----------------------------------------------------------------------
# 5. 작업 중단 및 세션 관리 로직
# ----------------------------------------------------------------------
active_sessions = {}

def cancel_request(task_id):
    if task_id in active_sessions:
        print(f"🛑 [작업 중단] 번역 task_id: {task_id} 요청을 중단합니다.")
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
# 6. 단일 텍스트 번역 함수
# ----------------------------------------------------------------------
def translate_text(text, task_id=None, unload_on_limit=True):
    """
    단일 셀 텍스트를 용어집(glossary)과 Ollama Gemma4 모델을 사용해 번역합니다.
    Markdown 기호나 문법 형식은 번역하지 않고 보존합니다.
    """
    global translation_count, session
    
    glossary = load_glossary("glossary.txt")
    
    # 동적 용어 필터링
    active_glossary = {}
    if glossary:
        combined_context = text.lower()
        for eng, kor in glossary.items():
            if eng.lower() in combined_context:
                active_glossary[eng] = kor

    # 용어집 규칙 문자열 가공
    glossary_section = ""
    if active_glossary:
        glossary_section = "5. MANDATORY Glossary mapping rule:\n"
        for eng, kor in active_glossary.items():
            glossary_section += f"   - Translate any forms of English term '{eng}' (case-insensitive) strictly into Korean '{kor}'.\n"
        glossary_section += "   - Never use any other Korean translations for these specific English terms.\n\n"

    system_prompt = (
        "You are a professional English-to-Korean translator. "
        "Translate the input English text into natural, academic, and clear Korean while strictly adhering to the following rules:\n\n"
        "1. Sentence Endings: Use ONLY formal plain style (해라체 - e.g., ~이다, ~한다, ~했다). Never use polite style (~해요, ~합니다, ~습니다) or informal friendly styles.\n"
        "2. Terminology & Proper Nouns: When translating general terminology, jargon, key concepts, or proper nouns, write the translated Korean term followed by the original English spelling in parentheses. (e.g., 스타일리스틱스(Stylistics), 페미니즘(Feminism)).\n"
        f"{glossary_section}"
        "3. Faithfulness: Translate strictly based on the source text. Keep the original meaning intact. Never add any extra explanations, notes, summaries, or details that are not present in the original text.\n"
        "4. Output format: Output ONLY the translated Korean text. Do not write any explanations, summaries, markdown headers, introduction ('Here is the translation:'), or conversational notes. Your response must consist solely of the translated text.\n"
        "5. References and Citations: If the target text is a bibliographical reference, citation, or book source information (e.g., author names, publication year, book/journal title, pages, publisher), do NOT translate it. Output the original English text exactly as it is.\n"
        "6. Markdown Formatting Protection: Do NOT translate or modify Markdown tags, symbols, or formatting syntax (such as headers `#`, bold/italic `*` or `**`, inline code blocks `` ` ``, code fence blocks, blockquotes `>`, list markers `-` or `*`, images `![]()`, or hyperlinks `[]()`). Keep these Markdown elements exactly as they are in the original text, and only translate the plain text content inside or around them."
    )

    prompt = f"<start_of_turn>system\n{system_prompt}<end_of_turn>\n<start_of_turn>user\n{text}<end_of_turn>\n<start_of_turn>model\n"

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "options": {
            "temperature": 0.2,
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
    translated = ""
    try:
        for attempt in range(1, max_retries + 1):
            try:
                # 모델이 언로드된 상태일 수 있으므로 타임아웃을 120초로 넉넉하게 지정합니다.
                response = req_session.post(OLLAMA_GENERATE_URL, json=payload, timeout=120)
                response.raise_for_status()
                result = response.json()
                translated = result["response"].strip()
                break
            except Exception as e:
                # 사용자가 요청을 중단(close) 시켜서 ConnectionError가 난 경우에는 재시도 없이 즉시 중단합니다.
                if task_id and task_id not in active_sessions:
                    print(f"🛑 [작업 중단 감지] task_id: {task_id} 재시도를 중단하고 빠져나갑니다.")
                    raise Exception("Task cancelled by user")
                
                last_error = e
                print(f"⚠️ Ollama API 번역 시도 {attempt}/{max_retries} 실패: {e}")
                if attempt < max_retries:
                    time.sleep(2 * attempt)  # 재시도 간격 점진적 증가
                else:
                    print("❌ 모든 번역 재시도 실패.")
                    raise last_error
    finally:
        if task_id and task_id in active_sessions:
            del active_sessions[task_id]

    # 셀 번역 카운터 증가 및 20회마다 메모리 정리 실행
    translation_count += 1
    if unload_on_limit and translation_count % 20 == 0:
        print(f"🧹 [메모리 최적화] {translation_count}회 번역 완료. VRAM 모델 언로드 및 세션을 갱신합니다...")
        try:
            unload_ollama_model()
        except Exception:
            pass
        session = requests.Session()

    translated = clean_thinking_process(translated)
    return translated
