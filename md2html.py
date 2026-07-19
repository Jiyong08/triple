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
# 3. PC 대조 뷰어, 메모 및 번역문 즉석 편집(contenteditable) 탑재형 HTML 생성기
# ----------------------------------------------------------------------
def generate_html(parsed_blocks, filename):
    # 각 블록 HTML 빌드 (원문, 번역문 편집기, 메모장 셀 배치)
    rows_html = ""
    for idx, block in enumerate(parsed_blocks):
        src_html = render_markdown(block["source"])
        trans_html = render_markdown(block["translation"])
        
        rows_html += f"""
        <div class="row" data-row-idx="{idx}">
            <!-- 1단 (왼쪽): 원문 셀 -->
            <div class="cell left-cell">
                <div class="cell-num">{idx + 1}</div>
                <div class="cell-content">{src_html}</div>
            </div>
            
            <!-- 2단 (가운데): 번역문 셀 (즉석 편집 가능) -->
            <div class="cell right-cell">
                <div class="cell-num">{idx + 1}</div>
                <div class="cell-content translation-section" contenteditable="true" data-trans-idx="{idx}" title="클릭하여 즉석에서 번역문을 수정할 수 있습니다.">
                    {trans_html}
                </div>
                <div class="cell-action-bar">
                    <button class="btn-write-memo" data-idx="{idx}">
                        ✍️ 메모 작성
                    </button>
                </div>
            </div>
            
            <!-- 3단 (오른쪽): 메모 셀 (기본 숨김, 메모 활성화 시 8:2 비율 연동 노출) -->
            <div class="memo-cell">
                <div class="memo-box-header">📝 메모</div>
                <textarea class="memo-input" data-card-idx="{idx}" placeholder="학습 메모를 입력하세요..."></textarea>
            </div>
        </div>
        """

    # PC 2분할/3분할 반응형, 로컬 스토리지 실시간 연동 메모 및 번역 수정 기능을 아우르는 프리미엄 HTML
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename} - PC 대조 리딩 & 즉석 편집 리포트</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0f1015;
            --bg-surface: #161822;
            --bg-header: #1e2230;
            --border-color: #2b3042;
            --text-primary: #e6e8f0;
            --text-secondary: #909bb4;
            --accent-color: #5865f2;
            --hover-row: #202436;
            --num-color: #4b526d;
            --memo-bg: #11121a;
            --edit-hover: #222538;
            --edit-focus: #0c0d12;
        }}

        body.light-theme {{
            --bg-primary: #f4f5f8;
            --bg-surface: #ffffff;
            --bg-header: #eef1f6;
            --border-color: #d1d6e5;
            --text-primary: #1f232e;
            --text-secondary: #5e6678;
            --accent-color: #3b4cca;
            --hover-row: #f0f3fa;
            --num-color: #949eb5;
            --memo-bg: #f9fafc;
            --edit-hover: #eaedf7;
            --edit-focus: #f4f6fa;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', 'Noto Sans KR', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            transition: background-color 0.3s, color 0.3s;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            line-height: 1.7;
        }}

        /* 상단 고정 헤더 */
        header {{
            position: sticky;
            top: 0;
            z-index: 100;
            background-color: var(--bg-header);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }}

        .header-title {{
            font-size: 1.1rem;
            font-weight: 600;
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
            border-radius: 8px;
            color: var(--text-primary);
            padding: 8px 14px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .header-btn:hover {{
            background-color: var(--hover-row);
            border-color: var(--accent-color);
        }}

        .header-btn:active {{
            transform: scale(0.97);
        }}

        /* 메모 활성화 버튼 피드백 */
        .header-btn.active {{
            background-color: var(--accent-color);
            border-color: var(--accent-color);
            color: #ffffff;
        }}

        /* 패널 헤더 표시기 (기본 원문/번역 2분할) */
        .panel-headers {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            background-color: var(--bg-surface);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 51px;
            z-index: 99;
            transition: grid-template-columns 0.25s ease-out;
        }}

        .panel-label {{
            padding: 12px 24px;
            font-weight: 600;
            font-size: 0.9rem;
            letter-spacing: -0.01em;
            text-transform: uppercase;
            color: var(--text-secondary);
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}

        .panel-label.left-label {{
            border-right: 1px solid var(--border-color);
            border-bottom-color: var(--accent-color);
        }}

        .panel-label.right-label {{
            border-bottom-color: #10b981;
        }}

        /* 메모 패널 헤더 (기본 숨김) */
        .panel-label.memo-label {{
            display: none;
            border-bottom-color: var(--accent-color);
        }}

        /* 메인 컨텐츠 컨테이너 */
        .content-container {{
            flex: 1;
            display: flex;
            flex-direction: column;
            width: 100%;
        }}

        /* 가로 분할 대조 행 (기본 원문/번역 1:1 분할) */
        .row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            border-bottom: 1px solid var(--border-color);
            transition: background-color 0.15s, grid-template-columns 0.25s ease-out;
        }}

        .row:hover {{
            background-color: var(--hover-row);
        }}

        /* 셀 공통 스타일 */
        .cell {{
            padding: 24px;
            position: relative;
            font-size: 0.96rem;
        }}

        .left-cell {{
            border-right: 1px solid var(--border-color);
        }}

        .right-cell {{
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        /* 행 번호 인디케이터 */
        .cell-num {{
            position: absolute;
            top: 10px;
            left: 10px;
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--num-color);
            user-select: none;
        }}

        /* 번역문 편집 에어리어 */
        .translation-section {{
            outline: none;
            padding: 8px;
            border-radius: 8px;
            border: 1px solid transparent;
            cursor: text;
            word-break: break-word;
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

        .cell-content {{
            word-break: break-word;
        }}

        .cell-content p, .translation-section p {{
            margin-bottom: 12px;
        }}
        
        .cell-content p:last-child, .translation-section p:last-child {{
            margin-bottom: 0;
        }}

        /* 셀별 액션바 (메모 작성 버튼 배치) */
        .cell-action-bar {{
            margin-top: 12px;
            display: flex;
            justify-content: flex-end;
        }}

        .btn-write-memo {{
            background-color: transparent;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-secondary);
            padding: 6px 12px;
            font-size: 0.8rem;
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

        /* 3단 분할 시 나타나는 메모장 셀 (기본 숨김) */
        .memo-cell {{
            display: none;
            opacity: 0;
            overflow: hidden;
            flex-direction: column;
            transition: opacity 0.25s ease-out;
        }}

        .memo-box-header {{
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--accent-color);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .memo-input {{
            flex: 1;
            width: 100%;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 0.85rem;
            resize: none;
            outline: none;
            transition: border-color 0.2s;
        }}

        .memo-input:focus {{
            border-color: var(--accent-color);
        }}

        /* --------------------------------------------------
           ★ PC 3단 분할 레이아웃 토글 CSS 클래스 (show-memos)
           * 전체 10 비율: 원문 4 / 번역문 4.8 / 메모 1.2 
           * 이를 통해 번역문:메모 비율을 정확히 [8:2] 로 구현!
           -------------------------------------------------- */
        .show-memos .panel-headers {{
            grid-template-columns: 4fr 4.8fr 1.2fr;
        }}

        .show-memos .panel-label.memo-label {{
            display: block;
            border-left: 1px solid var(--border-color);
        }}

        .show-memos .row {{
            grid-template-columns: 4fr 4.8fr 1.2fr;
        }}

        .show-memos .memo-cell {{
            display: flex;
            opacity: 1;
            border-left: 1px solid var(--border-color);
            padding: 24px 16px 16px 16px;
            background-color: var(--memo-bg);
        }}

        /* 마크다운 공통 타이포그래피 */
        .cell-content h1, .cell-content h2, .cell-content h3,
        .translation-section h1, .translation-section h2, .translation-section h3 {{
            margin: 16px 0 10px 0;
            font-weight: 600;
            line-height: 1.3;
        }}

        .cell-content h1 {{ font-size: 1.4rem; }}
        .cell-content h2 {{ font-size: 1.25rem; }}
        .cell-content h3 {{ font-size: 1.1rem; }}

        .cell-content ul, .cell-content ol,
        .translation-section ul, .translation-section ol {{
            margin-left: 20px;
            margin-bottom: 12px;
        }}

        .cell-content li, .translation-section li {{
            margin-bottom: 4px;
        }}

        /* 푸터 */
        footer {{
            text-align: center;
            padding: 20px;
            font-size: 0.8rem;
            color: var(--text-secondary);
            border-top: 1px solid var(--border-color);
            background-color: var(--bg-surface);
        }}
    </style>
</head>
<body>

    <header>
        <div class="header-title">
            📄 {filename} <span>PC 대조 & 즉석 편집 리포트</span>
        </div>
        <div class="header-controls">
            <button class="header-btn" id="memo-toggle-btn">
                <span>📝 메모 표시</span> <span class="toggle-status">꺼짐</span>
            </button>
            <button class="header-btn" id="theme-btn">
                <span id="theme-icon">☀️</span> <span id="theme-text">Light Mode</span>
            </button>
            <button class="header-btn" id="reset-data-btn" style="border-color: #ff4d4d; color: #ff4d4d;" title="작성한 메모 및 수정한 번역문을 초기화하고 원본 상태로 되돌립니다.">
                <span>🧹 초기화</span>
            </button>
        </div>
    </header>

    <div class="panel-headers">
        <div class="panel-label left-label">원문 (Source Text)</div>
        <div class="panel-label right-label">번역문 (Korean Translation)</div>
        <div class="panel-label memo-label">메모 (Notes)</div>
    </div>

    <div class="content-container">
        {rows_html}
    </div>

    <footer>
        PC MD to Dual Accordion HTML Converter (With Instant Edit & Memo) &copy; 2026. All rights reserved.
    </footer>

    <script>
        const themeBtn = document.getElementById('theme-btn');
        const themeIcon = document.getElementById('theme-icon');
        const themeText = document.getElementById('theme-text');
        
        const memoToggleBtn = document.getElementById('memo-toggle-btn');
        const appBody = document.body;
        
        // 1. 테마 스위칭 기능
        themeBtn.addEventListener('click', () => {{
            document.body.classList.toggle('light-theme');
            const isLight = document.body.classList.contains('light-theme');
            themeIcon.textContent = isLight ? '🌙' : '☀️';
            themeText.textContent = isLight ? 'Dark Mode' : 'Light Mode';
        }});

        // 2. PC 3단 분할 메모 토글
        memoToggleBtn.addEventListener('click', () => {{
            appBody.classList.toggle('show-memos');
            const isShowing = appBody.classList.contains('show-memos');
            memoToggleBtn.classList.toggle('active', isShowing);
            memoToggleBtn.querySelector('.toggle-status').textContent = isShowing ? "켜짐" : "꺼짐";
        }});

        // 3. 개별 셀 메모 작성 버튼 (클릭 시 메모창 활성화 및 포커싱)
        document.querySelectorAll('.btn-write-memo').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const idx = btn.getAttribute('data-idx');
                
                // 메모 창이 꺼져 있으면 자동으로 활성화
                if (!appBody.classList.contains('show-memos')) {{
                    memoToggleBtn.click();
                }}
                
                // 해당 카드의 메모 textarea 포커싱
                const targetTextarea = document.querySelector(`.memo-input[data-card-idx="${{idx}}"]`);
                if (targetTextarea) {{
                    targetTextarea.focus();
                }}
            }});
        }});

        // 4. 로컬 스토리지 연동 실시간 자동 저장 / 복원
        const DOC_KEY_PREFIX = "pc_memo_" + window.location.pathname + "_";
        const TRANS_KEY_PREFIX = "pc_trans_edit_" + window.location.pathname + "_";

        const memoInputs = document.querySelectorAll('.memo-input');
        const transSections = document.querySelectorAll('.translation-section');

        // 복원 로직
        memoInputs.forEach(input => {{
            const idx = input.getAttribute('data-card-idx');
            const savedValue = localStorage.getItem(DOC_KEY_PREFIX + idx);
            if (savedValue) {{
                input.value = savedValue;
            }}

            // 실시간 메모 저장
            input.addEventListener('input', () => {{
                localStorage.setItem(DOC_KEY_PREFIX + idx, input.value);
            }});
        }});

        transSections.forEach(section => {{
            const idx = section.getAttribute('data-trans-idx');
            const savedTrans = localStorage.getItem(TRANS_KEY_PREFIX + idx);
            if (savedTrans) {{
                section.innerHTML = savedTrans;
            }}

            // 번역문 즉석 편집 내용 실시간 저장
            section.addEventListener('input', () => {{
                localStorage.setItem(TRANS_KEY_PREFIX + idx, section.innerHTML);
            }});
        }});

        // 5. 일괄 데이터 초기화
        const resetDataBtn = document.getElementById('reset-data-btn');
        resetDataBtn.addEventListener('click', () => {{
            if (confirm("⚠️ 경고: 작성하신 모든 메모와 수정된 번역문 내용이 모두 삭제되고 원본 파일 내용으로 복원됩니다. 정말 초기화하시겠습니까?")) {{
                Object.keys(localStorage).forEach(key => {{
                    if (key.startsWith(DOC_KEY_PREFIX) || key.startsWith(TRANS_KEY_PREFIX)) {{
                        localStorage.removeItem(key);
                    }}
                }});
                alert("🧹 모든 데이터가 성공적으로 초기화되었습니다. 페이지를 새로고침합니다.");
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
    print("      트리플 MD ➡️ PC 대조형 즉석 편집 HTML 변환 앱 (md2html4pc)")
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
                output_filepath = os.path.join(dir_name, f"{base_name}_pc.html")
                
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                    
                print(f"🎉 PC용 HTML 변환 완료! 생성된 파일: {output_filepath}")
                
            except Exception as e:
                print(f"❌ {os.path.basename(filepath)} 변환 중 오류가 발생했습니다: {e}")
                
        print("\n✨ 지정된 파일들의 변환 처리가 모두 완료되었습니다!")

if __name__ == "__main__":
    main()
