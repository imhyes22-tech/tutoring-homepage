import pathlib, sys, urllib.parse

OUT = pathlib.Path(__file__).resolve().parent.parent   # 저장소 최상위 폴더
PHONE = "010-8241-2051"

NAV = [
    ("about.html", "와와 소개"),
    ("program.html", "과목 · 수업"),
    ("price.html", "수강료"),
    ("centers.html", "센터 찾기"),
    ("tutoring.html", "1:1 과외"),
    ("schedule.html", "학사일정"),
    ("class-status.html", "수업현황"),
]

def head(file, title, desc):
    url = "https://happyedu.co.kr/" + ("" if file == "index.html" else urllib.parse.quote(file))
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-96.png" type="image/png" sizes="96x96">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="naver-site-verification" content="31cf17236227568c555d790cddf1cc57daae2d2e" />
<!-- 검색 노출용 미리보기 (카카오톡·네이버 공유 시 표시) -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="해피에듀">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="ko_KR">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Jua&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
</head>
<body>
"""

def header():
    links = "\n".join(f'      <a href="/{h}">{t}</a>' for h, t in NAV)
    return f"""
<header>
  <div class="wrap nav">
    <a href="/" class="logo"><span class="logo-face">😊</span>해피에듀</a>
    <nav class="menu" id="menu">
{links}
    </nav>
    <a href="/contact.html" class="btn yellow">상담 신청</a>
    <button class="menu-toggle" aria-label="메뉴 열기">☰</button>
  </div>
</header>
"""

def page_hero(no, crumb, title, sub):
    return f"""
  <section class="page-hero">
    <div class="blob b1"></div><div class="blob b2"></div>
    <div class="wrap">
      <div class="crumb"><a href="/">홈</a> › {crumb}</div>
      <span class="chapter-no">{"CHAPTER " + no if no.isdigit() else no}</span>
      <h1>{title}</h1>
      <p>{sub}</p>
    </div>
  </section>
"""

def next_cta(href, label):
    return f"""
  <div class="wrap">
    <div class="next-cta">
      <a href="{href}" class="to-next"><small>다음 챕터 →</small><b>{label}</b></a>
      <a href="/contact.html" class="to-apply"><small>궁금한 건 상담으로 →</small><b>무료 상담 신청 ✏️</b></a>
    </div>
  </div>
"""

def footer(float_cta=True):
    fl = '\n<a href="/contact.html#apply" class="btn yellow float-cta" id="floatCta">💬 상담 신청</a>\n' if float_cta else '\n<a href="#apply" class="btn yellow float-cta" id="floatCta">💬 상담 신청</a>\n'
    return fl + f"""
<footer>
  <div class="wrap">
    <span class="foot-links"><a href="/schools.html">학교별 학원 · 과외 찾기</a> · <a href="/centers.html">센터 찾기</a> · <a href="/contact.html#faq">자주 묻는 질문</a></span>
    <span><strong>해피에듀</strong> · 와와학습코칭센터 마케팅 파트너 · 문의 <a href="tel:{PHONE}">{PHONE}</a></span>
    <span>본 사이트는 와와학습코칭센터 공식 홈페이지가 아닙니다. 와와학습코칭센터는 (주)동화세상에듀코의 브랜드입니다.</span>
    <span>© 2026 해피에듀</span>
  </div>
</footer>

<script src="/site.js"></script>
</body>
</html>
"""

def build(file, title, desc, body, contact_page=False, quiet=False):
    html = head(file, title, desc) + header() + "\n<main>\n" + body + "</main>\n" + footer(not contact_page)
    (OUT / file).parent.mkdir(parents=True, exist_ok=True)
    (OUT / file).write_text(html, encoding="utf-8", newline="\n")
    if not quiet: print("wrote", file)

def main():
    import json
    BODIES = pathlib.Path(sys.argv[1])
    for spec in json.loads((BODIES / "pages.json").read_text(encoding="utf-8")):
        body = (BODIES / spec["body"]).read_text(encoding="utf-8")
        body = body.replace("{{PHONE}}", PHONE)
        # 챕터 헤더/다음 챕터 자리표시자
        if "hero" in spec:
            body = page_hero(*spec["hero"]) + body
        if "next" in spec:
            body = body + next_cta(*spec["next"])
        build(spec["file"], spec["title"], spec["desc"], body, spec.get("contact", False))

if __name__ == "__main__":
    main()
