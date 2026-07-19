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
# 3. HTML 템플릿 생성기
# ----------------------------------------------------------------------
def generate_html(parsed_blocks, filename):
    # 각 블록 HTML 빌드
    rows_html = ""
    for idx, block in enumerate(parsed_blocks):
        src_html = render_markdown(block["source"])
        trans_html = render_markdown(block["translation"])
        
        rows_html += f"""
        <div class="row" data-row-idx="{idx}">
            <div class="cell left-cell">
                <div class="cell-num">{idx + 1}</div>
                <div class="cell-content">{src_html}</div>
            </div>
            <div class="cell right-cell">
                <div class="cell-num">{idx + 1}</div>
                <div class="cell-content">{trans_html}</div>
            </div>
        </div>
        """

    # 프리미엄 비주얼 디자인 및 반응형 스타일이 적용된 단일 HTML 완성본
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename} - 번역 대조 리포트</title>
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
            gap: 16px;
        }}

        /* 테마 토글 스위치 */
        .theme-toggle {{
            background: none;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            padding: 6px 12px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .theme-toggle:hover {{
            background-color: var(--hover-row);
            border-color: var(--accent-color);
        }}

        /* 패널 헤더 표시기 */
        .panel-headers {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            background-color: var(--bg-surface);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 57px;
            z-index: 99;
        }}

        .panel-label {{
            padding: 14px 24px;
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: -0.01em;
            text-transform: uppercase;
            color: var(--text-secondary);
            border-bottom: 2px solid transparent;
        }}

        .panel-label.left-label {{
            border-right: 1px solid var(--border-color);
            border-bottom-color: var(--accent-color);
        }}

        .panel-label.right-label {{
            border-bottom-color: #10b981; /* 번역문은 초록색 하이라이트 */
        }}

        /* 메인 컨텐츠 영역 */
        .content-container {{
            flex: 1;
            display: flex;
            flex-direction: column;
            width: 100%;
        }}

        /* 가로 분할 1:1 대조 행 */
        .row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            border-bottom: 1px solid var(--border-color);
            transition: background-color 0.15s;
        }}

        .row:hover {{
            background-color: var(--hover-row);
        }}

        /* 셀 디자인 */
        .cell {{
            padding: 24px;
            position: relative;
            line-height: 1.65;
            font-size: 0.95rem;
        }}

        .left-cell {{
            border-right: 1px solid var(--border-color);
        }}

        /* 행 번호 인디케이터 */
        .cell-num {{
            position: absolute;
            top: 12px;
            left: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--num-color);
            user-select: none;
        }}

        /* 마크다운 렌더링 텍스트 스타일링 */
        .cell-content {{
            word-break: break-word;
        }}

        .cell-content p {{
            margin-bottom: 12px;
        }}
        
        .cell-content p:last-child {{
            margin-bottom: 0;
        }}

        .cell-content h1, .cell-content h2, .cell-content h3 {{
            margin: 16px 0 10px 0;
            font-weight: 600;
            line-height: 1.3;
        }}

        .cell-content h1 {{ font-size: 1.4rem; }}
        .cell-content h2 {{ font-size: 1.25rem; }}
        .cell-content h3 {{ font-size: 1.1rem; }}

        .cell-content ul, .cell-content ol {{
            margin-left: 20px;
            margin-bottom: 12px;
        }}

        .cell-content li {{
            margin-bottom: 4px;
        }}

        .cell-content code {{
            background-color: rgba(255, 255, 255, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9rem;
        }}

        body.light-theme .cell-content code {{
            background-color: rgba(0, 0, 0, 0.06);
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
            📄 {filename} <span>번역 대조 리포트</span>
        </div>
        <div class="header-controls">
            <button class="theme-toggle" id="theme-btn">
                <span id="theme-icon">☀️</span> <span id="theme-text">Light Mode</span>
            </button>
        </div>
    </header>

    <div class="panel-headers">
        <div class="panel-label left-label">원문 (Source Text)</div>
        <div class="panel-label right-label">번역문 (Korean Translation)</div>
    </div>

    <div class="content-container">
        {rows_html}
    </div>

    <footer>
        Triple MD to Dual HTML Converter &copy; 2026. All rights reserved.
    </footer>

    <script>
        const themeBtn = document.getElementById('theme-btn');
        const themeIcon = document.getElementById('theme-icon');
        const themeText = document.getElementById('theme-text');
        
        // 시스템 다크모드 인식 및 테마 토글 설정
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
    print("      Triple MD 파일 ➡️ 2분할 대조 HTML 변환 앱 (3md2html)")
    print("=" * 60)
    
    while True:
        filepath = input("📂 변환할 트리플 MD 파일 경로를 입력하세요 (종료: Enter): ").strip()
        if not filepath:
            print("👋 프로그램을 종료합니다.")
            return

        # 경로 문자열 다듬기 (복사 시 들어가는 큰따옴표/작은따옴표 제거)
        filepath = filepath.replace('"', '').replace("'", "")
        
        if not os.path.exists(filepath):
            print(f"❌ 파일을 찾을 수 없습니다: {filepath}\n올바른 경로인지 다시 확인해 주세요.\n")
            continue
            
        break

    print(f"\n⚡ 파일 로딩 중: {filepath}")
    
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
            print("❌ 파싱 실패: 파일 내에서 유효한 번역문 또는 원문 데이터를 추출하지 못했습니다.")
            return

        print(f"🔍 총 {len(parsed_blocks)}개의 대조 단락을 성공적으로 감지 및 파싱했습니다.")
        
        # 3. HTML 템플릿 바인딩 및 렌더링
        html_content = generate_html(parsed_blocks, os.path.basename(filepath))
        
        # 4. 결과 파일 저장 (.md -> .html)
        dir_name = os.path.dirname(filepath)
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        output_filepath = os.path.join(dir_name, f"{base_name}.html")
        
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print("\n✨" + "=" * 50)
        print("🎉 HTML 변환이 성공적으로 완료되었습니다!")
        print(f"💾 생성된 파일: {output_filepath}")
        print("💡 생성된 HTML 파일을 더블클릭하시면 오프라인 브라우저에서 바로 확인하실 수 있습니다.")
        print("=" * 52)
        
    except Exception as e:
        import traceback
        print(f"\n❌ 변환 중 오류가 발생했습니다: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
