"""수업현황 글 빌드 (GitHub Actions에서 저장할 때마다 자동 실행)

content/class/*.md  (관리 화면 Pages CMS에서 쓰는 글)
  → class/{파일이름}.html   글 페이지
  → class-posts.js         수업현황 목록 데이터
  → sitemap.xml            /class/ 주소 갱신
images/class/*           올린 사진: 긴 변 1600px로 줄이고 위치(GPS) 등 사진 정보 삭제, HEIC → JPG

로컬에서 직접 돌릴 때:  python tools/build_cms.py
(사진 처리는 Pillow가 설치된 곳에서만 실행돼요)
"""
import json, re, sys, html, pathlib, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import gen

esc = lambda s: html.escape(str(s or ""), quote=True)
CONTENT, IMAGES, OUTDIR = ROOT / "content" / "class", ROOT / "images" / "class", ROOT / "class"
CENTERS = {c["n"]: c for c in json.loads((ROOT / "tools" / "data" / "centers.json").read_text(encoding="utf-8"))}
SCHOOLS = {}
for name, short, region, gu, url in json.loads((ROOT / "schools-index.json").read_text(encoding="utf-8")):
    SCHOOLS.setdefault(name, url); SCHOOLS.setdefault(short, url)
EMOJI = {"수학": "📐", "영어": "🔤", "국어": "📖", "과학": "🔬", "사회": "🌏", "한국사": "🏛️"}


# ---------- 사진 처리 ----------
def process_images():
    try:
        from PIL import Image, ImageOps
    except ImportError:
        print("Pillow 없음: 사진 처리 건너뜀"); return {}
    try:
        import pillow_heif; pillow_heif.register_heif_opener()
    except ImportError:
        pass
    renamed = {}
    for p in sorted(IMAGES.glob("*")):
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"): continue
        im = Image.open(p)
        if p.suffix.lower() in (".jpg", ".jpeg") and max(im.size) <= 1600 and not im.getexif():
            continue                                  # 이미 처리된 사진
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((1600, 1600))
        out = p.with_suffix(".jpg")
        im.save(out, "JPEG", quality=82, optimize=True)   # exif를 넘기지 않으므로 사진 정보가 지워짐
        if out != p:
            p.unlink(); renamed[f"/images/class/{p.name}"] = f"/images/class/{out.name}"
        print("사진 처리:", out.name)
    return renamed


# ---------- 글 읽기 (YAML 앞머리 + 본문) ----------
def parse_front(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m: return {}, text
    raw, body = m.groups()
    try:
        import yaml
        return yaml.safe_load(raw) or {}, body
    except ImportError:
        pass
    data, key = {}, None                               # 간단한 YAML (key: value, - 목록)
    for line in raw.splitlines():
        if re.match(r"^\s+-\s", line) and key:
            data.setdefault(key, []).append(unquote(line.split("-", 1)[1].strip()))
        elif ":" in line and not line.startswith(" "):
            key, val = line.split(":", 1); key, val = key.strip(), val.strip()
            data[key] = unquote(val) if val else []
    return data, body

def unquote(v):
    if v == "[]": return []
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"": v = v[1:-1].replace("''", "'")
    return {"true": True, "false": False}.get(v, v)

def dump_front(data, body):
    lines = ["---"]
    for k, v in data.items():
        if isinstance(v, list):
            if not v: lines.append(f"{k}: []"); continue
            lines.append(f"{k}:"); lines += [f"  - {json.dumps(x, ensure_ascii=False)}" for x in v]
        elif isinstance(v, bool): lines.append(f"{k}: {'true' if v else 'false'}")
        else: lines.append(f"{k}: {json.dumps(str(v), ensure_ascii=False)}")
    return "\n".join(lines) + "\n---\n" + body


def body_html(body):
    b = body.strip()
    if b.startswith("<"): return b                     # 관리 화면 rich-text(HTML) 또는 기존 글
    try:
        import markdown
        return markdown.markdown(b, extensions=["extra", "nl2br"])
    except ImportError:
        return "".join(f"<p>{esc(p).replace(chr(10), '<br>')}</p>" for p in re.split(r"\n\s*\n", b) if p.strip())

def plain(h): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


# ---------- 빌드 ----------
def main():
    renamed = process_images()
    entries = []
    for md in sorted(CONTENT.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        data, body = parse_front(text)
        if renamed:                                    # HEIC 등 이름이 바뀐 사진 경로 고치기
            new = text
            for a, b in renamed.items(): new = new.replace(a, b)
            if new != text: md.write_text(new, encoding="utf-8"); data, body = parse_front(new)
        if data.get("published") is False: continue
        title = str(data.get("title") or "").strip()
        if not title: continue
        slug, date = md.stem, str(data.get("date") or md.stem[:10])[:10]
        branch, subject, school = data.get("branch") or "", data.get("subject") or "", data.get("school") or ""
        c = CENTERS.get(branch)
        photos = data.get("photos") or []
        if isinstance(photos, str): photos = [photos]
        cover = data.get("cover") or ""          # 지점 사진이 없을 때 쓰는 본사 제공 교실 사진
        bh = body_html(body)
        excerpt = str(data.get("excerpt") or "").strip() or plain(bh)[:110]
        emoji = data.get("emoji") or EMOJI.get(subject, "📸")
        area = data.get("area") or (c["a"].split()[1] if c else "")
        school_url = SCHOOLS.get(school)

        gallery = "".join(f'<img src="{esc(p)}" alt="{esc(title)} 사진 {i}" loading="lazy">' for i, p in enumerate(photos, 1))
        cover_html = "" if photos or not cover else (
            f'<figure class="post-cover"><img src="{esc(cover)}" alt="와와학습코칭센터 교실 (본사 제공 사진)" loading="lazy">'
            f'<figcaption>와와학습코칭센터 교실 · 본사 제공 사진 (지점 사진 아님)</figcaption></figure>')
        sub = " · ".join(x for x in [date.replace("-", "."), f"와와 {branch}" if branch else "", school] if x)
        center = ""
        if c:
            q = "/contact.html?" + urllib.parse.urlencode({k: v for k, v in dict(center=branch, region=c["r"], school=school, subject=subject).items() if v}) + "#apply"
            center = f'''
      <h2>와와 {esc(branch)}</h2>
      <div class="card center">
        <h3>와와 {esc(branch)}</h3>
        <p class="addr">📍 {esc(c["a"])}</p>
        <div class="center-btns">
          <a class="btn white" href="https://map.naver.com/p/search/{esc(c["a"])}" target="_blank" rel="noopener">지도 보기</a>
          <a class="btn yellow" href="{esc(q)}">이 지점 상담 신청</a>
        </div>
      </div>'''
        links = (f'<a href="{school_url}">🏫 {esc(school)} 학원 · 과외 · 학사일정</a> ' if school_url else "") + '<a href="/class-status.html">📋 다른 수업현황 글 보기</a>'
        page = gen.page_hero(f"{emoji} {esc(branch or '수업현황')}", f'<a href="/class-status.html">수업현황</a>' + (f" › {esc(area)}" if area else ""),
                             esc(title), esc(sub)) + f'''
  <article class="block post-body">
    <div class="wrap narrow">
      {f'<div class="post-photos">{gallery}</div>' if gallery else cover_html}
      {bh}
{center}
      <p class="post-links">{links}</p>
    </div>
  </article>
'''
        gen.build(f"class/{slug}.html", f"{esc(title)} | 해피에듀", esc(excerpt[:150]), page, quiet=True)
        entries.append(dict(slug=slug, region=c["r"] if c else "", area=area, branch=branch, school=school, subject=subject or "기타",
                            date=date, emoji=emoji, thumb=photos[0] if photos else cover, title=title, excerpt=excerpt))

    # 지워진 글의 페이지 삭제
    keep = {e["slug"] for e in entries}
    for f in OUTDIR.glob("*.html"):
        if f.stem not in keep: f.unlink(); print("삭제:", f.name)

    entries.sort(key=lambda e: (e["date"], e["slug"]), reverse=True)
    (ROOT / "class-posts.js").write_text("// 수업현황 글 목록 (tools/build_cms.py가 자동으로 만듦 — 직접 고치지 마세요)\nwindow.CLASS_POSTS = "
                                         + json.dumps(entries, ensure_ascii=False) + ";\n", encoding="utf-8")
    sm = ROOT / "sitemap.xml"
    s = re.sub(r"  <url><loc>https://happyedu\.co\.kr/class/[^<]*</loc></url>\n", "", sm.read_text(encoding="utf-8"))
    s = s.replace("</urlset>", "".join(f"  <url><loc>https://happyedu.co.kr/class/{urllib.parse.quote(e['slug'])}.html</loc></url>\n" for e in entries) + "</urlset>")
    sm.write_text(s, encoding="utf-8", newline="\n")
    print("수업현황 글", len(entries))

if __name__ == "__main__":
    main()
