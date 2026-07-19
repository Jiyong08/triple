import os
import sys
import subprocess

# ----------------------------------------------------------------------
# 1. 의존성 패키지 자동 설치 로직 (pywebview)
# ----------------------------------------------------------------------
def install_dependencies():
    required = {'pywebview'}
    installed = set()
    
    try:
        import webview
    except ImportError:
        installed.add('pywebview')
        
    if installed:
        print("💡 데스크톱 앱 구동에 필요한 라이브러리를 설치합니다:", installed)
        try:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            subprocess.check_call([sys.executable, "-m", "pip", "install", *installed], env=env)
            print("✅ 필수 라이브러리 설치 완료.\n")
        except Exception as e:
            print(f"❌ 패키지 자동 설치 실패: {e}")
            print("수동 설치 권장: pip install pywebview")
            sys.exit(1)

# 의존성 확인 및 설치
install_dependencies()

# 라이브러리 임포트
import webview
import tri_translate         # Ollama 번역 모듈 임포트
import tri_translate_deepl   # DeepL 번역 모듈 임포트
import tri_summary           # Ollama 요약 모듈 임포트
import tri_summary_gemini    # Gemini 요약 모듈 임포트

# JS에서 호출 가능한 Python API 클래스 정의 (self.window 제거로 COM 무한 재귀 리플렉션 오류 완벽 차단)
class Api:
    def translate(self, text, method="ollama", api_key=None, task_id=None, unload_on_limit=True):
        """
        자바스크립트에서 window.pywebview.api.translate(text, method, api_key, task_id, unload_on_limit)로 호출하는 번역 함수
        """
        try:
            if method == "deepl":
                translated = tri_translate_deepl.translate_text(text, task_id, api_key)
            else:
                translated = tri_translate.translate_text(text, task_id, unload_on_limit)
            return {"success": True, "result": translated}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def unload_vram(self):
        """
        배치 번역(전체 번역) 종료 후 수동으로 VRAM 모델을 정리하고 파이썬 가비지 컬렉션을 동작시킵니다.
        """
        try:
            import gc
            # Ollama GPU 메모리 언로드 요청
            tri_translate.unload_ollama_model()
            # 파이썬 프로세스 자체 가비지 컬렉터 강제 구동
            gc.collect()
            print("🧹 [백엔드 메모리 최적화] 수동 VRAM 언로드 및 파이썬 GC 완료.")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def summarize(self, text, method="ollama", api_key=None, task_id=None):
        """
        자바스크립트에서 window.pywebview.api.summarize(text, method, api_key, task_id)로 호출하는 요약 함수
        """
        try:
            if method == "gemini":
                summarized = tri_summary_gemini.summarize_text(text, task_id, api_key)
            else:
                summarized = tri_summary.summarize_text(text, task_id)
            return {"success": True, "result": summarized}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cancel_task(self, task_id):
        """
        진행 중인 번역/요약 작업을 중단시킵니다.
        """
        if not task_id:
            return {"success": False, "error": "Invalid task_id"}
        
        if task_id.startswith("translate_"):
            res1 = tri_translate.cancel_request(task_id)
            res2 = tri_translate_deepl.cancel_request(task_id)
            return {"success": res1 or res2}
        elif task_id.startswith("summarize_"):
            res1 = tri_summary.cancel_request(task_id)
            res2 = tri_summary_gemini.cancel_request(task_id)
            return {"success": res1 or res2}
        
        return {"success": False, "error": "Unknown task_id type"}

    def save_file_dialog(self, default_name, content):
        """
        자바스크립트에서 호출 가능한 파일 저장 다이얼로그 기능.
        이 프로그램이 실행된 위치를 디폴트 경로로 설정하여 저장 다이얼로그를 띄우고 파일로 저장합니다.
        """
        active_window = webview.active_window()
        if not active_window:
            return {"success": False, "error": "Active window not found"}
        try:
            # 디폴트 디렉터리 설정 (프로그램이 실행된 현재 위치)
            default_dir = os.path.abspath(os.getcwd())
            
            # default_name에 따른 확장자 필터 지정
            ext = os.path.splitext(default_name)[1].lower() # .md or .txt
            if ext == '.md':
                file_types = 'Obsidian Markdown (*.md)'
            else:
                file_types = 'Text Files (*.txt)'
            
            # 저장 파일 다이얼로그 호출 (file_types 및 save_filename 설정)
            file_path = active_window.create_file_dialog(
                webview.SAVE_DIALOG,
                directory=default_dir,
                save_filename=default_name,
                file_types=[file_types, 'All Files (*.*)']
            )
            
            if not file_path:
                # 사용자가 취소한 경우
                return {"success": False, "cancelled": True}

            # pywebview 버전에 따라 튜플 또는 리스트로 반환될 수 있으므로 문자열 경로 추출
            # (중첩 튜플 형태인 경우를 대비해 while 루프로 완벽하게 해제)
            while isinstance(file_path, (tuple, list)):
                if len(file_path) > 0 and file_path[0] is not None:
                    file_path = file_path[0]
                else:
                    return {"success": False, "cancelled": True}
                
            # 사용자가 저장 다이얼로그에서 직접 확장자를 치지 않고 저장한 경우 보정 처리
            if ext and isinstance(file_path, str) and not file_path.lower().endswith(ext):
                base, current_ext = os.path.splitext(file_path)
                if not current_ext:
                    file_path = file_path + ext
                
            # 파일 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return {"success": True, "path": file_path}
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print("❌ 파일 저장 실패 상세 에러 로그:")
            print(tb)
            return {"success": False, "error": f"{str(e)}\n{tb}"}

def main():
    # 최적화된 index2.html 파일의 절대 경로 구하기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, 'index.html')
    
    if not os.path.exists(html_path):
        print(f"❌ 오류: '{html_path}' 파일을 찾을 수 없습니다. index.html 파일이 같은 폴더에 있는지 확인해 주세요.")
        sys.exit(1)
        
    print("🚀 triple 데스크톱 어플리케이션을 시작합니다...")
    
    # API 인스턴스 생성
    api = Api()
    
    # 윈도우 창 생성 (index2.html 로드)
    webview.create_window(
        title='triple - 고성능 번역 및 요약 에디터',
        url=html_path,
        width=1280,
        height=720,
        resizable=True,
        min_size=(800, 600),
        text_select=True, # 텍스트 드래그 및 복사 가능 설정
        js_api=api        # Python-JS 브릿지 등록
    )
    
    # pywebview 루프 시작
    webview.start()

if __name__ == '__main__':
    main()
