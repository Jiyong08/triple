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
# 3. 태블릿 맞춤형 HTML 템플릿 생성기
# ----------------------------------------------------------------------
def generate_html(parsed_blocks, filename):
    # 각 블록 HTML 빌드
    cards_html = ""
    for idx, block in enumerate(parsed_blocks):
        src_html = render_markdown(block["source"])
        trans_html = render_markdown(block["translation"])
        
        cards_html += f"""
        <div class="card" data-idx="{idx}">
            <div class="card-num">{idx + 1}</div>
            <div class="translation-section">
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
        </div>
        """

    # 태블릿 터치 스크린 및 시원시원한 가독성에 맞춘 최적화 템플릿
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{filename} - 태블릿 리딩 리포트</title>
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
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent; /* 모바일 터치 하이라이트 제거 */
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

        /* 태블릿 반응형 뷰포트 고정 */
        .app-container {{
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            flex: 1;
        }}

        /* 상단 고정 헤더 */
        header {{
            position: sticky;
            top: 0;
            z-index: 100;
            background-color: var(--bg-header);
            border-bottom: 1px solid var(--border-color);
            padding: 16px 24px;
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

        /* 테마 토글 스위치 (터치 감도를 위해 넉넉한 사이즈 부여) */
        .theme-toggle {{
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

        .theme-toggle:active {{
            transform: scale(0.97);
        }}

        /* 메인 컨텐츠 리딩 에어리어 */
        main {{
            flex: 1;
            padding: 24px 16px;
        }}

        /* 태블릿 독서 카드 */
        .card {{
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 18px;
            padding: 28px;
            margin-bottom: 24px;
            position: relative;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            transition: all 0.2s;
        }}

        .card:hover {{
            border-color: var(--accent-color);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
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

        /* 한글 번역문 섹션 (기본 노출) */
        .translation-section {{
            font-size: 1.08rem; /* 태블릿 가독성에 최적화된 큰 텍스트 */
            color: var(--text-primary);
            margin-bottom: 12px;
            word-break: break-word;
        }}

        .translation-section p {{
            margin-bottom: 12px;
        }}

        .translation-section p:last-child {{
            margin-bottom: 0;
        }}

        /* 원문 아코디언 접기 상자 */
        .source-details {{
            margin-top: 18px;
            border-top: 1px dashed var(--border-color);
            padding-top: 18px;
        }}

        /* 아코디언 헤더 (터치 영역 확보를 위해 padding을 넓게 배치) */
        .source-summary {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 20px;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            color: var(--text-secondary);
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            list-style: none; /* 기본 삼각형 숨김 */
            transition: all 0.2s;
        }}

        .source-summary:hover {{
            border-color: var(--accent-color);
            color: var(--text-primary);
        }}

        .source-summary:active {{
            transform: scale(0.98);
        }}

        /* Chrome/Safari 기본 접기 아이콘 강제 제거 */
        .source-summary::-webkit-details-marker {{
            display: none;
        }}

        .summary-arrow {{
            font-size: 0.9rem;
            transition: transform 0.2s;
            color: var(--accent-color);
        }}

        /* 아코디언 열렸을 때 화살표 회전 및 헤더 스타일 전환 */
        details[open] .summary-arrow {{
            transform: rotate(180deg);
        }}

        details[open] .source-summary {{
            border-bottom-left-radius: 0;
            border-bottom-right-radius: 0;
            border-color: var(--accent-color);
            background-color: var(--hover-card);
        }}

        /* 영어 원문 컨텐츠 본문 */
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
            animation: slideDown 0.2s ease-out;
        }}

        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-5px); }}
            to {{ opacity: 1; transform: translateY(0); }}
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
                📖 {filename} <span>태블릿 대조 노트</span>
            </div>
            <div class="header-controls">
                <button class="theme-toggle" id="theme-btn">
                    <span id="theme-icon">☀️</span> <span id="theme-text">Light Mode</span>
                </button>
            </div>
        </header>

        <main>
            {cards_html}
        </main>

        <footer>
            Tablet MD to Accordion HTML Converter &copy; 2026.
        </footer>
    </div>

    <script>
        const themeBtn = document.getElementById('theme-btn');
        const themeIcon = document.getElementById('theme-icon');
        const themeText = document.getElementById('theme-text');
        
        // 태블릿 모드 테마 스위칭 핸들러
        themeBtn.addEventListener('click', () => {{
            document.body.classList.toggle('light-theme');
            const isLight = document.body.classList.contains('light-theme');
            themeIcon.textContent = isLight ? '🌙' : '☀️';
            themeText.textContent = isLight ? 'Dark Mode' : 'Light Mode';
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
