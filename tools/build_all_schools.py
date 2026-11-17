"""전국 초·중·고 학교별 1:1 과외 · 학원 · 학사일정 페이지 생성
usage: python -I build_all_schools.py <gen.py 폴더> <데이터 폴더>
"""
import json, sys, re, html, pathlib, collections, urllib.parse

GEN_DIR, DATA = sys.argv[1], pathlib.Path(sys.argv[2])
sys.path.insert(0, GEN_DIR)
import gen

esc = lambda s: html.escape(str(s), quote=True)
KINDS = ["초등학교", "중학교", "고등학교"]
REGION_OF = {"서울특별시": "서울", "경기도": "경기", "인천광역시": "인천", "부산광역시": "부산", "대구광역시": "대구",
             "전남광주통합특별시(광주)": "광주", "전남광주통합특별시(전남)": "전남", "대전광역시": "대전", "울산광역시": "울산",
             "세종특별자치시": "세종", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
             "전북특별자치도": "전북", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주"}
REGIONS = list(dict.fromkeys(REGION_OF.values()))
SLUG = {"서울": "seoul", "경기": "gyeonggi", "인천": "incheon", "부산": "busan", "대구": "daegu", "광주": "gwangju",
        "전남": "jeonnam", "대전": "daejeon", "울산": "ulsan", "세종": "sejong", "강원": "gangwon", "충북": "chungbuk",
        "충남": "chungnam", "전북": "jeonbuk", "경북": "gyeongbuk", "경남": "gyeongnam", "제주": "jeju"}
SUBJECTS = {"초등학교": ["수학", "영어", "국어"], "중학교": ["수학", "영어", "국어", "과학", "사회"],
            "고등학교": ["수학", "영어", "국어", "과학", "사회", "한국사"]}

# ---------- 데이터 ----------
schools = [r for r in json.loads((DATA / "all_schools.json").read_text(encoding="utf-8"))
           if r["SCHUL_KND_SC_NM"] in KINDS and not r["SCHUL_NM"].startswith("(가칭)") and r["LCTN_SC_NM"] in REGION_OF
           and r.get("ORG_RDNMA")]
matched = json.loads((DATA / "schools_matched.json").read_text(encoding="utf-8"))   # 와와 지점 인근 학교 (코드 → 지점)
old_urls = set(json.loads((DATA / "school_urls.json").read_text(encoding="utf-8")))
centers = [c for c in json.loads(pathlib.Path(GEN_DIR, "centers.json").read_text(encoding="utf-8")) if c["b"] == "와와학습코칭센터"]

def short(name):
    n = re.sub(r'^서울(?=.+초등학교$)', '', name)
    for a, b in (("여자고등학교", "여고"), ("여자중학교", "여중"), ("고등학교", "고"), ("중학교", "중"), ("초등학교", "초")):
        if n.endswith(a): return n[: -len(a)] + b
    return n

for s in schools:
    parts = s["ORG_RDNMA"].split()
    s["region"] = REGION_OF[s["LCTN_SC_NM"]]
    s["city"] = parts[1] if len(parts) > 1 else s["region"]
    s["gu"] = (parts[1] + " " + parts[2]) if len(parts) > 2 and parts[1].endswith("시") and parts[2].endswith("구") else s["city"]
    s["short"] = short(s["SCHUL_NM"])

# 파일 이름: 기존 주소는 그대로 유지, 이름이 겹치면 지역을 붙임
name_count = collections.Counter(s["SCHUL_NM"] for s in schools)
used = set()
for s in sorted(schools, key=lambda s: s["SD_SCHUL_CODE"] not in matched):
    plain = f"school/{s['SCHUL_NM']}.html"
    if "/" + urllib.parse.quote(plain) in old_urls and s["SD_SCHUL_CODE"] in matched:
        f = plain
    elif name_count[s["SCHUL_NM"]] == 1 and plain not in used:
        f = plain
    else:
        f = f"school/{s['SCHUL_NM']}-{s['gu'].replace(' ', '')}.html"
        if f in used: f = f"school/{s['SCHUL_NM']}-{s['SD_SCHUL_CODE']}.html"
    used.add(f)
    s["file"], s["url"] = f, "/" + urllib.parse.quote(f)

lost = old_urls - {s["url"] for s in schools}
print("old urls kept:", len(old_urls) - len(lost), "lost:", len(lost))

by_gu = collections.defaultdict(list)
for s in schools: by_gu[(s["region"], s["gu"])].append(s)

# 학교 → 와와 지점: 지점 자료에 '인근 학교'로 나온 곳이 우선, 없으면 같은 시 · 구의 지점
def nearby_centers(s):
    if s["SD_SCHUL_CODE"] in matched:
        return "근처", [{"n": c["center"], "a": c["addr"], "r": c["region"]} for c in matched[s["SD_SCHUL_CODE"]]["centers"]]
    same = [c for c in centers if c["a"].split()[1:2] == [s["city"]]]
    gu2 = s["gu"].split()[-1]
    same.sort(key=lambda c: gu2 not in c["a"])
    return "같은 지역", [{"n": c["n"], "a": c["a"], "r": c["r"]} for c in same[:3]]

def contact(**kw): return "/contact.html?" + urllib.parse.urlencode(kw) + "#apply"

def info_rows(s):
    rows = [("학교 종류", s.get("HS_SC_NM") or s["SCHUL_KND_SC_NM"]), ("설립 구분", s.get("FOND_SC_NM")),
            ("남녀 구분", s.get("COEDU_SC_NM")),
            ("설립", f'{s["FOND_YMD"][:4]}년' if s.get("FOND_YMD") else None),
            ("관할 교육청", s.get("JU_ORG_NM")), ("주소", s["ORG_RDNMA"])]
    out = "".join(f"<tr><th>{k}</th><td>{esc(v)}</td></tr>" for k, v in rows if v)
    hp = (s.get("HMPG_ADRES") or "").strip()
    if hp and hp not in ("http://", "https://"):
        if not hp.startswith("http"): hp = "http://" + hp
        out += f'<tr><th>학교 홈페이지</th><td><a href="{esc(hp)}" target="_blank" rel="noopener nofollow" style="text-decoration:underline">바로가기</a></td></tr>'
    return out

def school_page(s):
    sh, nm = esc(s["short"]), esc(s["SCHUL_NM"])
    label, cs = nearby_centers(s)
    if cs:
        cards = "\n".join(f'''          <article class="card center">
            <div class="center-top"><span class="tag-r">{esc(c["r"])}</span></div>
            <h3>와와 {esc(c["n"])}</h3>
            <p class="addr">📍 {esc(c["a"])}</p>
            <div class="center-btns">
              <a class="btn white" href="https://map.naver.com/p/search/{esc(c["a"])}" target="_blank" rel="noopener">지도 보기</a>
              <a class="btn yellow" href="{esc(contact(center=c["n"], region=c["r"], school=s["SCHUL_NM"]))}">이 지점 상담 신청</a>
            </div>
          </article>''' for c in cs)
        academy = f'''
  <section class="block" id="academy">
    <div class="wrap">
      <div class="sec-head">
        <span class="pill">🏫 ACADEMY</span>
        <h2>{sh} {label} 와와학습코칭센터</h2>
        <p>학원에서 스스로 공부하는 습관까지 잡고 싶다면, 가까운 와와 지점도 함께 알아보세요.</p>
      </div>
      <div class="centers">
{cards}
      </div>
    </div>
  </section>
'''
    else:
        academy = ""
    subj = "".join(f'<a class="btn white" href="{esc(contact(type="tutor", school=s["SCHUL_NM"], subject=x))}">{sh} {x} 과외</a>'
                   for x in SUBJECTS[s["SCHUL_KND_SC_NM"]])
    sib = [o for o in by_gu[(s["region"], s["gu"])] if o is not s]
    sib.sort(key=lambda o: (o["SCHUL_KND_SC_NM"] != s["SCHUL_KND_SC_NM"], o["SCHUL_NM"]))
    sib_html = "".join(f'<a href="{o["url"]}">{esc(o["SCHUL_NM"])}</a>' for o in sib[:16])
    region_url = f'/schools/{SLUG[s["region"]]}.html'
    codes = json.dumps({k: s[k] for k in ("ATPT_OFCDC_SC_CODE", "SD_SCHUL_CODE", "SCHUL_KND_SC_NM")})

    body = gen.page_hero(f"🏫 {s['gu']}",
                         f'<a href="/schools.html">학교별 찾기</a> › <a href="{region_url}">{esc(s["region"])}</a> › <a href="{region_url}#{esc(s["gu"])}">{esc(s["gu"])}</a>',
                         f'{nm}<br><span class="sub-h1">1:1 과외 · 학원 · 학사일정</span>',
                         f'📍 {esc(s["ORG_RDNMA"])}') + f'''
  <section class="block" id="tutor">
    <div class="wrap">
      <div class="sec-head">
        <span class="pill">🤝 1:1</span>
        <h2>{sh} 1:1 과외</h2>
        <p>{nm} 학생 한 명만을 위한 수업이에요. 선생님이 집으로 가거나, 화상으로 전국 어디서나 수업해요.</p>
      </div>
      <div class="prices" style="grid-template-columns:repeat(2,1fr);max-width:720px;margin:0 auto">
        <div class="card price"><div class="bubble c-mint">🏠</div><h3>방문 과외</h3><span class="lv">선생님이 집으로</span>
          <ul><li>시간당 <b>3.2 ~ 4.7<small>만원</small></b></li></ul></div>
        <div class="card price"><div class="bubble c-sky">💻</div><h3>화상 과외</h3><span class="lv">어디서든 온라인으로</span>
          <ul><li>시간당 <b>2.95 ~ 4.1<small>만원</small></b></li></ul></div>
      </div>
      <p class="note">* 와와 본사((주)동화세상에듀코) 1:1 과외 기준 참고용 금액이에요. 방문 과외는 지역에 따라 선생님 배정이 어려울 수 있어요. <a href="/tutoring.html" style="text-decoration:underline">1:1 과외 자세히 보기</a></p>
      <div class="subj-btns">{subj}</div>
    </div>
  </section>

  <section class="block" id="sch">
    <div class="wrap">
      <div class="sec-head">
        <span class="pill">📅 CALENDAR</span>
        <h2>{sh} 학사일정</h2>
        <p>시험 기간 · 방학 · 휴업일을 미리 확인하고, 시험 4주 전부터 준비해요. (앞으로 6개월)</p>
      </div>
      <div class="region-chips" id="schGrades"></div>
      <div class="sch-legend">
        <span class="ev-exam">📝 시험</span><span class="ev-break">🏖️ 방학 · 개학</span><span class="ev-off">😴 휴업일</span><span class="ev-etc">📌 행사</span>
      </div>
      <div class="sch-list" id="schList"><p class="sch-msg">학사일정을 불러오는 중…</p></div>
    </div>
  </section>

  <section class="block" id="info">
    <div class="wrap">
      <div class="sec-head">
        <span class="pill">ℹ️ SCHOOL</span>
        <h2>{nm} 정보</h2>
      </div>
      <div class="compare card info-table"><table><tbody>{info_rows(s)}</tbody></table></div>
      <p class="note">* 학교 정보와 학사일정은 나이스 교육정보 개방 포털 공공데이터 기준이에요. 해피에듀는 학교와 제휴 관계가 없어요.</p>
    </div>
  </section>
{academy}
  <section class="block" id="nearby">
    <div class="wrap">
      <div class="sec-head">
        <span class="pill">🗺️ NEARBY</span>
        <h2>{esc(s["gu"])} 다른 학교</h2>
      </div>
      <div class="school-links">{sib_html}</div>
    </div>
  </section>

  <div class="wrap">
    <div class="next-cta">
      <a href="{region_url}#{esc(s["gu"])}" class="to-next"><small>다른 학교 보기 →</small><b>{esc(s["region"])} 학교 목록</b></a>
      <a href="{esc(contact(type="tutor", school=s["SCHUL_NM"]))}" class="to-apply"><small>{sh} 학생 상담 →</small><b>과외 · 학원 상담 신청 ✏️</b></a>
    </div>
  </div>

  <script src="/schedule.js"></script>
  <script>
    Schedule.show({codes}, {{ grades: document.getElementById('schGrades'), list: document.getElementById('schList') }})
      .catch(() => {{ document.getElementById('schList').innerHTML = '<p class="sch-msg">학사일정을 불러오지 못했어요.</p>'; }});
  </script>
'''
    subj_kw = " · ".join(f"{s['short']} {x} 과외" for x in SUBJECTS[s["SCHUL_KND_SC_NM"]][:3])
    title = f'{s["SCHUL_NM"]} 1:1 과외 · 학원 · 학사일정 | 해피에듀'
    desc = (f'{s["SCHUL_NM"]}({s["gu"]}) 학생을 위한 1:1 방문 · 화상 과외와 와와학습코칭센터 안내. '
            f'{subj_kw}, {s["short"]} 시험 기간 · 학사일정까지 한 번에 확인하세요.')
    gen.build(s["file"], title, esc(desc), body, quiet=True)

for i, s in enumerate(schools):
    school_page(s)
    if i % 2000 == 0: print("school pages", i, flush=True)

# ---------- 지역별 목록 ----------
for r in REGIONS:
    rs = [s for s in schools if s["region"] == r]
    gus = sorted({s["gu"] for s in rs})
    toc = "".join(f'<a href="#{esc(g)}">{esc(g)} <small>{len(by_gu[(r, g)])}</small></a>' for g in gus)
    blocks = []
    for g in gus:
        lst = sorted(by_gu[(r, g)], key=lambda x: (KINDS.index(x["SCHUL_KND_SC_NM"]), x["SCHUL_NM"]))
        rows = []
        for k in KINDS:
            ks = [x for x in lst if x["SCHUL_KND_SC_NM"] == k]
            if ks:
                rows.append(f'<p class="kind-label">{k} {len(ks)}</p><div class="school-links">' +
                            "".join(f'<a href="{x["url"]}" data-k="{esc(x["SCHUL_NM"] + " " + x["short"])}">{esc(x["SCHUL_NM"])}</a>' for x in ks) + "</div>")
        blocks.append(f'      <div class="gu-block" id="{esc(g)}"><h3>{esc(g)} <small>{len(lst)}개 학교</small></h3>{"".join(rows)}</div>')
    body = gen.page_hero(f"🏫 {r}", f'<a href="/schools.html">학교별 찾기</a> › {r}', f"{r} 학교별<br>1:1 과외 · 학원 찾기",
                         f"{r} 초 · 중 · 고 {len(rs)}개 학교. 학교를 누르면 1:1 과외, 학사일정, 가까운 와와 지점을 볼 수 있어요.") + f'''
  <section class="block">
    <div class="wrap">
      <div class="finder-search"><input type="search" id="schoolQ" placeholder="🔍 {r} 학교 이름으로 찾기" aria-label="학교 검색"></div>
      <div class="gu-toc">{toc}</div>
{chr(10).join(blocks)}
    </div>
  </section>
  <script>
    (() => {{
      const q = document.getElementById('schoolQ');
      q.addEventListener('input', () => {{
        const w = q.value.trim().split(/\\s+/).filter(Boolean);
        document.querySelectorAll('.gu-block').forEach(b => {{
          let shown = 0;
          b.querySelectorAll('a').forEach(a => {{ const ok = w.every(x => a.dataset.k.includes(x)); a.hidden = !ok; if (ok) shown++; }});
          b.hidden = !shown;
        }});
      }});
    }})();
  </script>
'''
    gen.build(f"schools/{SLUG[r]}.html", f"{r} 학교별 1:1 과외 · 학원 · 학사일정 | 해피에듀",
              f"{r} 초등학교 · 중학교 · 고등학교 {len(rs)}곳의 학교별 1:1 과외(방문 · 화상), 와와학습코칭센터, 학사일정 안내.", body, quiet=True)

# ---------- 전국 목록 (검색용 인덱스 포함) ----------
index = [[s["SCHUL_NM"], s["short"], s["region"], s["gu"], s["url"]] for s in schools]
(gen.OUT / "schools-index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
cards = "".join(f'<a class="card region-card" href="/schools/{SLUG[r]}.html"><b>{r}</b><span>{sum(s["region"] == r for s in schools):,}개 학교</span></a>' for r in REGIONS)
body = gen.page_hero("🏫 SCHOOLS", "학교별 찾기", "우리 학교<br>1:1 과외 · 학원 찾기",
                     f"전국 초 · 중 · 고 {len(schools):,}개 학교. 학교를 누르면 1:1 과외, 학사일정, 가까운 와와 지점을 한 번에 볼 수 있어요.") + f'''
  <section class="block" id="schools">
    <div class="wrap">
      <div class="finder-search"><input type="search" id="schoolQ" placeholder="🔍 학교 이름으로 찾기 (예: 사직고, 대치중)" aria-label="학교 검색" autocomplete="off"></div>
      <div class="school-links search-results" id="schoolHits"></div>
      <div class="region-cards">{cards}</div>
      <p class="note">* 학교 정보는 나이스 교육정보 개방 포털 공공데이터 기준이에요. 목록에 없는 학교도 <a href="/contact.html" style="text-decoration:underline">상담 신청</a>에 학교 이름을 남겨 주시면 안내해 드려요.</p>
    </div>
  </section>
  <script>
    (() => {{
      const q = document.getElementById('schoolQ'), out = document.getElementById('schoolHits');
      let idx = null;
      const esc = s => s.replace(/[&<>"']/g, ch => '&#' + ch.charCodeAt(0) + ';');
      async function load() {{ if (!idx) idx = await (await fetch('/schools-index.json')).json(); return idx; }}
      q.addEventListener('focus', load, {{ once: true }});
      q.addEventListener('input', async () => {{
        const w = q.value.trim().split(/\\s+/).filter(Boolean);
        if (!w.length) {{ out.innerHTML = ''; return; }}
        const hits = (await load()).filter(s => w.every(x => (s[0] + ' ' + s[1] + ' ' + s[2] + ' ' + s[3]).includes(x))).slice(0, 40);
        out.innerHTML = hits.length ? hits.map(s => `<a href="${{s[4]}}">${{esc(s[0])}} <small>${{esc(s[2])}} ${{esc(s[3])}}</small></a>`).join('')
                                    : '<p class="sch-msg">찾는 학교가 없어요.</p>';
      }});
    }})();
  </script>
'''
gen.build("schools.html", "전국 학교별 1:1 과외 · 학원 · 학사일정 | 해피에듀",
          f"전국 초 · 중 · 고 {len(schools):,}개 학교별 1:1 과외(방문 · 화상), 와와학습코칭센터, 학사일정 안내. 학교 이름으로 바로 찾아보세요.", body)

urls = [s["url"] for s in schools] + [f"/schools/{SLUG[r]}.html" for r in REGIONS]
(DATA / "all_school_urls.json").write_text(json.dumps(urls, ensure_ascii=False), encoding="utf-8")
print("schools", len(schools), "regions", len(REGIONS))
