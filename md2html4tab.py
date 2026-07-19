import os
import sys
import subprocess
import re

# ----------------------------------------------------------------------
# 1. 의존성 패키지 자동 설치 및 임포트 로직
# ----------------------------------------------------------------------
def install_dependencies():
    required = {'markdown'}
    installed = set()
    
    try:
        import markdown
    except ImportError:
        installed.add('markdown')
        
    if installed:
        print("💡 HTML 변환에 필요한 라이브러리를 설치합니다:", installed)
        try:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            subprocess.check_call([sys.executable, "-m", "pip", "install", *installed], env=env)
            print("✅ 필수 라이브러리 설치 완료.\n")
        except Exception as e:
            print(f"⚠️ 라이브러리 자동 설치 실패: {e}")
            print("수동 설치 권장: pip install markdown")
            print("기본 텍스트 모드로 변환을 시도합니다.")

install_dependencies()

try:
    import markdown
except ImportError:
    markdown = None

# ----------------------------------------------------------------------
# 2. 마크다운 변환 함수
# ----------------------------------------------------------------------
def render_markdown(text):
    if not text:
        return ""
    if markdown:
        try:
            return markdown.markdown(text, extensions=['extra'])
        except Exception:
            pass
    # 폴백: 개행 처리 등 단순 치환
    escaped = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return f"<p>{escaped.replace('\n', '<br/>')}</p>"

# ----------------------------------------------------------------------
# 3. 태블릿, 메모 및 번역문 즉석 편집(contenteditable) 탑재형 HTML 생성기
# ----------------------------------------------------------------------
def generate_html(parsed_blocks, filename):
    # 각 블록 HTML 빌드 (메모 영역 및 편집 가능한 번역문 적용)
    cards_html = ""
    for idx, block in enumerate(parsed_blocks):
        src_html = render_markdown(block["source"])
        trans_html = render_markdown(block["translation"])
        
        cards_html += f"""
        <div class="card" data-idx="{idx}">
            <div class="card-num">{idx + 1}</div>
            
            <div class="card-layout-wrapper">
                <!-- 왼쪽 영역: 번역문(즉석 편집 가능) 및 원문 아코디언 -->
                <div class="main-content-area">
                    <div class="translation-section" contenteditable="true" data-trans-idx="{idx}" title="터치하여 직접 번역문을 수정할 수 있습니다.">
                        {trans_html}
                    </div>
                    
                    <details class="source-details">
                        <summary class="source-summary">
                            <span class="summary-title">🔍 원문 보기 (Show Original)</span>
                            <span class="summary-arrow">▾</span>
                        </summary>
                        <div class="source-content">
                            {src_html}
                        </div>
                    </details>
                    
                    <div class="card-action-bar">
                        <button class="btn-write-memo" data-idx="{idx}">
                            ✍️ 메모 작성
                        </button>
                    </div>
                </div>
                
                <!-- 오른쪽 영역: 메모장 셀 (기본 숨김, 8:2 화면 분할 적용 대상) -->
                <div class="memo-area">
                    <div class="memo-box-header">📝 메모 셀</div>
                    <textarea class="memo-input" data-card-idx="{idx}" placeholder="여기에 학습 메모를 입력하세요..."></textarea>
                </div>
            </div>
        </div>
        """

    # 태블릿 터치 스크린, 8:2 화면 분할, 로컬 스토리지 메모 & 번역문 실시간 수정을 결합한 단일 HTML
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{filename} - 태블릿 대조 리딩 & 즉석 편집 노트</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0b0c10;
            --bg-surface: #12131a;
            --bg-header: #1a1c24;
            --border-color: #242735;
            --text-primary: #f0f2f5;
            --text-secondary: #a0aabf;
            --accent-color: #5865f2;
            --hover-card: #181a24;
            --num-color: #4b526d;
            --memo-bg: #1c1e2b;
            --edit-hover: #1e2030;
            --edit-focus: #0f1015;
        }}

        body.light-theme {{
            --bg-primary: #f0f2f5;
            --bg-surface: #ffffff;
            --bg-header: #e4e7eb;
            --border-color: #ced4da;
            --text-primary: #1a1d24;
            --text-secondary: #5a6275;
            --accent-color: #2b3a8f;
            --hover-card: #f8f9fa;
            --num-color: #8e98a9;
            --memo-bg: #f3f4f8;
            --edit-hover: #f1f3f7;
            --edit-focus: #f8f9fa;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }}

        body {{
            font-family: 'Inter', 'Noto Sans KR', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            transition: background-color 0.3s, color 0.3s;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            line-height: 1.75;
        }}

        /* 태블릿 반응형 최대 너비 설정 (메모 셀 노출을 위해 1100px로 확장) */
        .app-container {{
            width: 100%;
            max-width: 1100px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            flex: 1;
            transition: max-width 0.3s;
        }}

        /* 상단 고정 헤더 */
        header {{
            position: sticky;
            top: 0;
            z-index: 100;
            background-color: var(--bg-header);
            border-bottom: 1px solid var(--border-color);
            padding: 14px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }}

        .header-title {{
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}

        .header-title span {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 400;
            margin-left: 8px;
        }}

        .header-controls {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        /* 공통 헤더 제어 버튼 */
        .header-btn {{
            background: none;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            color: var(--text-primary);
            padding: 10px 18px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .header-btn:active {{
            transform: scale(0.97);
        }}

        /* 메모표시 활성화 버튼 하이라이트 */
        .header-btn.active {{
            background-color: var(--accent-color);
            border-color: var(--accent-color);
            color: #ffffff;
        }}

        /* 메인 컨텐츠 영역 */
        main {{
            flex: 1;
            padding: 24px 16px;
        }}

        /* 태블릿 독서 카드 */
        .card {{
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 18px;
            padding: 24px;
            margin-bottom: 24px;
            position: relative;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            transition: all 0.2s;
        }}

        .card:hover {{
            border-color: var(--accent-color);
        }}

        /* 행 번호 배지 */
        .card-num {{
            position: absolute;
            top: -10px;
            left: 20px;
            background-color: var(--accent-color);
            color: #ffffff;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 2px 10px;
            border-radius: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            user-select: none;
        }}

        /* 가로 카드 레이아웃 구조 */
        .card-layout-wrapper {{
            display: flex;
            gap: 20px;
            width: 100%;
        }}

        /* 번역문/원문 메인 텍스트 셀 (메모 비활성화 시 100%, 활성화 시 80%) */
        .main-content-area {{
            width: 100%;
            transition: width 0.25s ease-out;
        }}

        /* 번역문 섹션 (더블클릭/터치 즉석 수정 인터페이스 추가) */
        .translation-section {{
            font-size: 1.08rem;
            color: var(--text-primary);
            margin-bottom: 12px;
            word-break: break-word;
            outline: none;
            padding: 8px;
            border-radius: 10px;
            border: 1px solid transparent;
            cursor: text;
            transition: all 0.2s;
        }}

        .translation-section:hover {{
            background-color: var(--edit-hover);
            border-color: var(--border-color);
        }}

        .translation-section:focus {{
            background-color: var(--edit-focus);
            border-color: var(--accent-color);
            box-shadow: 0 0 0 3px rgba(88, 101, 242, 0.15);
        }}

        .translation-section p {{
            margin-bottom: 12px;
        }}

        .translation-section p:last-child {{
            margin-bottom: 0;
        }}

        /* 원문 아코디언 접기 상자 */
        .source-details {{
            margin-top: 16px;
            border-top: 1px dashed var(--border-color);
            padding-top: 16px;
        }}

        .source-summary {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 18px;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            color: var(--text-secondary);
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            list-style: none;
            transition: all 0.2s;
        }}

        .source-summary::-webkit-details-marker {{
            display: none;
        }}

        .summary-arrow {{
            font-size: 0.9rem;
            transition: transform 0.2s;
            color: var(--accent-color);
        }}

        details[open] .summary-arrow {{
            transform: rotate(180deg);
        }}

        details[open] .source-summary {{
            border-bottom-left-radius: 0;
            border-bottom-right-radius: 0;
            border-color: var(--accent-color);
            background-color: var(--hover-card);
        }}

        .source-content {{
            padding: 20px;
            background-color: var(--hover-card);
            border: 1px solid var(--border-color);
            border-top: none;
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
            font-size: 0.98rem;
            color: var(--text-secondary);
            word-break: break-word;
        }}

        /* 카드별 액션바 (메모 작성 버튼 배치) */
        .card-action-bar {{
            margin-top: 14px;
            display: flex;
            justify-content: flex-end;
        }}

        .btn-write-memo {{
            background-color: transparent;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-secondary);
            padding: 8px 14px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .btn-write-memo:hover {{
            border-color: var(--accent-color);
            color: var(--text-primary);
        }}

        .btn-write-memo:active {{
            transform: scale(0.96);
        }}

        /* 오른쪽 메모장 셀 (기본 숨김, 활성화 시 20% 분할 레이아웃 노출) */
        .memo-area {{
            display: none;
            width: 0;
            opacity: 0;
            overflow: hidden;
            flex-direction: column;
            border-left: 2px solid var(--border-color);
            padding-left: 0;
            transition: width 0.25s ease-out, opacity 0.25s ease-out, padding-left 0.25s ease-out;
        }}

        .memo-box-header {{
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--accent-color);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .memo-input {{
            flex: 1;
            width: 100%;
            background-color: var(--memo-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 0.9rem;
            resize: none;
            outline: none;
            transition: border-color 0.2s;
        }}

        .memo-input:focus {{
            border-color: var(--accent-color);
        }}

        /* --------------------------------------------------
           ★ 8:2 화면 레이아웃 토글 CSS 클래스 (show-memos)
           -------------------------------------------------- */
        .show-memos .main-content-area {{
            width: 80%; /* 번역문+원문 80% */
        }}

        .show-memos .memo-area {{
            display: flex;
            width: 20%; /* 메모장 셀 20% */
            opacity: 1;
            padding-left: 20px;
        }}

        /* 마크다운 공통 타이포그래피 */
        .source-content h1, .source-content h2, .source-content h3,
        .translation-section h1, .translation-section h2, .translation-section h3 {{
            margin: 16px 0 10px 0;
            font-weight: 600;
            line-height: 1.3;
        }}

        .source-content h1 {{ font-size: 1.4rem; }}
        .source-content h2 {{ font-size: 1.25rem; }}
        .source-content h3 {{ font-size: 1.1rem; }}

        .source-content ul, .source-content ol,
        .translation-section ul, .translation-section ol {{
            margin-left: 24px;
            margin-bottom: 12px;
        }}

        .source-content li, .translation-section li {{
            margin-bottom: 4px;
        }}

        /* 푸터 */
        footer {{
            text-align: center;
            padding: 24px 16px;
            font-size: 0.8rem;
            color: var(--text-secondary);
            border-top: 1px solid var(--border-color);
            background-color: var(--bg-surface);
            margin-top: auto;
        }}
    </style>
</head>
<body>

    <div class="app-container">
        <header>
            <div class="header-title">
                📖 {filename} <span>태블릿 대조 & 즉석 편집 노트</span>
            </div>
            <div class="header-controls">
                <button class="header-btn" id="memo-toggle-btn">
                    <span>📝 메모 표시</span> <span class="toggle-status">꺼짐</span>
                </button>
                <button class="header-btn" id="theme-btn">
                    <span id="theme-icon">☀️</span> <span id="theme-text">Light Mode</span>
                </button>
                <button class="header-btn" id="reset-data-btn" style="border-color: #ff4d4d; color: #ff4d4d;" title="작성한 메모 및 수정한 번역문을 초기화하고 원본 텍스트로 되돌립니다.">
                    <span>🧹 초기화</span>
                </button>
            </div>
        </header>

        <main>
            {cards_html}
        </main>

        <footer>
            Tablet MD to Accordion HTML Converter (With Instant Edit) &copy; 2026.
        </footer>
    </div>

    <script>
        const themeBtn = document.getElementById('theme-btn');
        const themeIcon = document.getElementById('theme-icon');
        const themeText = document.getElementById('theme-text');
        
        const memoToggleBtn = document.getElementById('memo-toggle-btn');
        const appContainer = document.querySelector('.app-container');
        
        // 1. 시스템 테마 스위칭 핸들러
        themeBtn.addEventListener('click', () => {{
            document.body.classList.toggle('light-theme');
            const isLight = document.body.classList.contains('light-theme');
            themeIcon.textContent = isLight ? '🌙' : '☀️';
            themeText.textContent = isLight ? 'Dark Mode' : 'Light Mode';
        }});

        // 2. 메모 셀 8:2 토글 컨트롤러
        memoToggleBtn.addEventListener('click', () => {{
            appContainer.classList.toggle('show-memos');
            const isShowing = appContainer.classList.contains('show-memos');
            memoToggleBtn.classList.toggle('active', isShowing);
            memoToggleBtn.querySelector('.toggle-status').textContent = isShowing ? "켜짐" : "꺼짐";
        }});

        // 3. 메모 작성 버튼 핸들러 (클릭 시 자동으로 메모 셀을 켜고 입력창 포커싱)
        document.querySelectorAll('.btn-write-memo').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const idx = btn.getAttribute('data-idx');
                
                // 메모 창이 꺼져 있으면 자동으로 활성화
                if (!appContainer.classList.contains('show-memos')) {{
                    memoToggleBtn.click();
                }}
                
                // 해당 카드의 메모 textarea 포커싱 및 스크롤
                const targetTextarea = document.querySelector(`.memo-input[data-card-idx="${{idx}}"]`);
                if (targetTextarea) {{
                    targetTextarea.focus();
                }}
            }});
        }});

        // 4. 로컬 스토리지 연동 자동 저장 / 복원 로직
        const DOC_KEY_PREFIX = "triple_memo_" + window.location.pathname + "_";
        const TRANS_KEY_PREFIX = "triple_trans_edit_" + window.location.pathname + "_";

        const memoInputs = document.querySelectorAll('.memo-input');
        const transSections = document.querySelectorAll('.translation-section');

        // 저장된 메모 데이터 및 번역문 수정본 자동 복원
        memoInputs.forEach(input => {{
            const idx = input.getAttribute('data-card-idx');
            const savedValue = localStorage.getItem(DOC_KEY_PREFIX + idx);
            if (savedValue) {{
                input.value = savedValue;
            }}

            // 메모 실시간 저장
            input.addEventListener('input', () => {{
                localStorage.setItem(DOC_KEY_PREFIX + idx, input.value);
            }});
        }});

        transSections.forEach(section => {{
            const idx = section.getAttribute('data-trans-idx');
            const savedTrans = localStorage.getItem(TRANS_KEY_PREFIX + idx);
            
            // 사용자가 예전에 수정했던 번역문 텍스트가 있으면 덮어쓰기 복원
            if (savedTrans) {{
                section.innerHTML = savedTrans;
            }}

            // 번역문 즉석 편집 시 실시간 자동 저장
            section.addEventListener('input', () => {{
                localStorage.setItem(TRANS_KEY_PREFIX + idx, section.innerHTML);
            }});
        }});

        // 5. 메모 및 수정된 번역문 일괄 초기화 버튼 동작
        const resetDataBtn = document.getElementById('reset-data-btn');
        resetDataBtn.addEventListener('click', () => {{
            if (confirm("⚠️ 경고: 작성하신 모든 메모와 사용자가 수정한 번역문 텍스트가 전부 초기화되고 원본 내용으로 복원됩니다. 정말 초기화하시겠습니까?")) {{
                // 이 문서에 연동된 모든 LocalStorage 데이터 삭제
                Object.keys(localStorage).forEach(key => {{
                    if (key.startsWith(DOC_KEY_PREFIX) || key.startsWith(TRANS_KEY_PREFIX)) {{
                        localStorage.removeItem(key);
                    }}
                }});
                alert("🧹 모든 메모 및 번역문 수정 이력이 초기화되었습니다. 페이지를 새로고침합니다.");
                window.location.reload();
            }}
        }});
    </script>
</body>
</html>
"""
    return html_template

# ----------------------------------------------------------------------
# 4. 메인 실행 제어 로직
# ----------------------------------------------------------------------
def main():
    # 콘솔 인코딩 교정
    if sys.platform.startswith('win'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stdin.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("      트리플 MD ➡️ 태블릿 최적화 접이식 HTML 변환 앱 (md2html4tab)")
    print("=" * 60)
    
    while True:
        print("\n" + "-" * 60)
        print("💡 여러 파일을 한 번에 변환하려면 경로를 세미콜론(;)으로 구분하여 입력해 주세요.")
        print("   예: C:\\path\\file1.md; C:\\path\\file2.md")
        filepaths_input = input("📂 변환할 트리플 MD 파일 경로를 입력하세요 (종료: Enter): ").strip()
        
        if not filepaths_input:
            print("👋 프로그램을 종료합니다.")
            break
            
        # 세미콜론(;)으로 파일 경로 분할
        raw_paths = filepaths_input.split(';')
        valid_paths = []
        
        for p in raw_paths:
            p_clean = p.strip().replace('"', '').replace("'", "")
            if not p_clean:
                continue
            if not os.path.exists(p_clean):
                print(f"❌ 파일을 찾을 수 없습니다: {p_clean} (해당 파일은 건너뜁니다.)")
                continue
            valid_paths.append(p_clean)
            
        if not valid_paths:
            print("⚠️ 변환 가능한 올바른 파일 경로가 존재하지 않습니다. 다시 입력해 주세요.")
            continue
            
        print(f"\n⚡ 총 {len(valid_paths)}개의 파일 변환 작업을 시작합니다...")
        
        for filepath in valid_paths:
            print(f"\n🔄 변환 중: {filepath}")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 1. <br/> 또는 <br> 태그를 기준으로 블록 분할
                blocks = re.split(r'<br\s*/?>', content)
                
                parsed_blocks = []
                for block in blocks:
                    block = block.strip()
                    if not block:
                        continue
                        
                    # 2. 정규식 패턴을 사용하여 원문과 번역문 추출 (요약문 정보는 고의로 무시 및 폐기)
                    trans_match = re.search(r'<summary>번역문</summary>\s*([\s\S]*?)\s*</details>', block)
                    src_match = re.search(r'<summary>원문</summary>\s*([\s\S]*?)\s*</details>', block)
                    
                    if trans_match or src_match:
                        translation = trans_match.group(1).strip() if trans_match else ""
                        source = src_match.group(1).strip() if src_match else ""
                    else:
                        # details 태그가 전혀 없는 단일 텍스트 형태 (isAllSame 처리 블록인 경우)
                        clean_text = re.sub(r'<[^>]+>', '', block).strip()
                        translation = clean_text
                        source = clean_text
                        
                    # 둘 다 아예 비어있으면 노이즈 블록으로 간주하고 건너뜀
                    if not translation and not source:
                        continue
                        
                    parsed_blocks.append({
                        "source": source,
                        "translation": translation
                    })
                    
                if not parsed_blocks:
                    print(f"❌ 파싱 실패: {os.path.basename(filepath)} 파일 내에서 유효한 번역문 또는 원문 데이터를 추출하지 못했습니다.")
                    continue

                print(f"🔍 총 {len(parsed_blocks)}개의 대조 단락 파싱 완료.")
                
                # 3. HTML 템플릿 바인딩 및 렌더링
                html_content = generate_html(parsed_blocks, os.path.basename(filepath))
                
                # 4. 결과 파일 저장 (.md -> .html)
                dir_name = os.path.dirname(filepath)
                base_name = os.path.splitext(os.path.basename(filepath))[0]
                output_filepath = os.path.join(dir_name, f"{base_name}_tablet.html")
                
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                    
                print(f"🎉 태블릿용 HTML 변환 완료! 생성된 파일: {output_filepath}")
                
            except Exception as e:
                print(f"❌ {os.path.basename(filepath)} 변환 중 오류가 발생했습니다: {e}")
                
        print("\n✨ 지정된 파일들의 변환 처리가 모두 완료되었습니다!")

if __name__ == "__main__":
    main()
