"""와와 지점 상세 페이지 (center/{지점명}.html) + 센터 찾기 카드에 '자세히 보기' 연결

data: tools/data/center_details.json  (본사 공식 사이트 지점 상세 정보 — 본사 사용 허락)
      tools/data/schools_matched.json (지점 근처 학교 ↔ 나이스 학교 코드)
usage: python tools/build_centers.py
"""
import json, re, sys, html, pathlib, collections, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import gen

esc = lambda s: html.escape(str(s or ""), quote=True)
details = json.loads((ROOT / "tools/data/center_details.json").read_text(encoding="utf-8"))
matched = json.loads((ROOT / "tools/data/schools_matched.json").read_text(encoding="utf-8"))
slim = json.loads((ROOT / "tools/data/schools_slim.json").read_text(encoding="utf-8"))   # [이름, 약칭, 지역, 구, url, 교육청, 코드, 종류]
GRADES = ["초1", "초2", "초3", "초4", "초5", "초6", "중1", "중2", "중3", "고1", "고2", "고3"]
PRICE = {"서울": {"초등": (14, 21, 35), "중등": (15, 22.5, 37.5), "고등": (17, 25.5, 42.5)},
         "기타": {"초등": (12, 18, 30), "중등": (13, 19.5, 32.5), "고등": (15, 22.5, 37.5)}}
REGION_LONG = {"서울": "서울", "경기": "경기", "인천": "인천", "대전": "대전", "세종": "세종", "충남": "충남", "충북": "충북", "전북": "전북",
               "전남광주": ("광주", "전남"), "부산": "부산", "울산": "울산", "대구": "대구", "경북": "경북", "경남": "경남", "강원": "강원", "제주": "제주"}

def short(name):
    n = re.sub(r'^서울(?=.+초등학교$)', '', name)
    for a, b in (("여자고등학교", "여고"), ("여자중학교", "여중"), ("고등학교", "고"), ("중학교", "중"), ("초등학교", "초")):
        if n.endswith(a): return n[: -len(a)] + b
    return n

# 지점별 근처 학교 (나이스 코드 있음)
by_center = collections.defaultdict(dict)
for code, s in matched.items():
    for c in s["centers"]:
        by_center[c["center"]][short(s["SCHUL_NM"])] = s
by_region = collections.defaultdict(list)
for row in slim: by_region[row[2]].append(row)

def school_link(sh, center, region, gu):
    """지점 자료의 학교 약칭(예: 매봉중) → (우리 학교 페이지 url, 나이스 정보). 이름 끝이 같고 같은 시 · 구인 학교를 찾는다."""
    regions = REGION_LONG.get(region, region); regions = regions if isinstance(regions, tuple) else (regions,)
    rows = [r for rg in regions for r in by_region[rg] if r[1] == sh or r[1].endswith(sh)]
    exact = [r for r in rows if r[1] == sh]
    rows = exact or rows
    near = [r for r in rows if gu and gu in r[3]]
    pick = near[0] if len(near) == 1 else (rows[0] if len(rows) == 1 else None)
    if not pick: return None, None
    return pick[4], {"SCHUL_NM": pick[0], "ATPT_OFCDC_SC_CODE": pick[5], "SD_SCHUL_CODE": pick[6], "SCHUL_KND_SC_NM": pick[7]}

def center_url(name): return "/center/" + urllib.parse.quote(name) + ".html"

pages = []
for c in details:
    name, region, info, grades = c["name"], c["region"], c["info"], c["grades"]
    addr = info.get("주소", "")
    parts = addr.split()
    gu = parts[1] if len(parts) > 1 else ""
    dong = info.get("센터", "").split()[0] if info.get("센터") else ""
    subjects = [x for x in re.split(r"[·,]\s*", info.get("가능 과목", "")) if x]
    q = "/contact.html?" + urllib.parse.urlencode(dict(center=name, region=region)) + "#apply"

    # 인근 학교 칩 (+ 학사일정용 코드)
    exam_schools, school_html = [], ""
    for label, key in (("초등학교", "인근 초등학교"), ("중학교", "인근 중학교"), ("고등학교", "인근 고등학교")):
        names = [x.strip() for x in info.get(key, "").split(",") if x.strip()]
        if not names: continue
        chips = []
        for sh in names:
            url, s = school_link(sh, name, region, gu)
            chips.append(f'<a href="{url}">{esc(sh)}</a>' if url else f'<span>{esc(sh)}</span>')
            if s and s["SCHUL_KND_SC_NM"] in ("중학교", "고등학교"):
                exam_schools.append({"n": short(s["SCHUL_NM"]), "u": url, "o": s["ATPT_OFCDC_SC_CODE"], "c": s["SD_SCHUL_CODE"]})
        school_html += f'<p class="kind-label">{label}</p><div class="school-links">{"".join(chips)}</div>'
    apts = [x.strip() for x in info.get("인근 아파트", "").split(",") if x.strip()]

    # 과목별 개설 학년표
    grade_rows = ""
    for subj, gs in grades.items():
        have = {g.strip() for g in gs.split(",")}
        grade_rows += f"<tr><th>{esc(subj)}</th>" + "".join(f'<td class="{"on" if g in have else ""}">{"●" if g in have else ""}</td>' for g in GRADES) + "</tr>"

    price = PRICE["서울" if region == "서울" else "기타"]
    price_rows = "".join(f'<tr><th>{lv}</th>' + "".join(f"<td>{v}만원</td>" for v in vals) + "</tr>" for lv, vals in price.items())
    info_rows = "".join(f"<tr><th>{k}</th><td>{esc(v)}</td></tr>" for k, v in
                        (("주소", addr), ("인근 지하철역", info.get("인근 지하철역")), ("가능 과목", " · ".join(subjects)),
                         ("학원 등록번호", info.get("등록번호"))) if v)

    body = gen.page_hero(f"📍 {esc(region)}", f'<a href="/centers.html">센터 찾기</a> › {esc(region)}',
                         f'와와학습코칭센터<br>{esc(name)}', f'{esc(dong)} · {esc(addr)}') + f'''
  <section class="block center-detail">
    <div class="wrap narrow">
      <div class="center-cta card">
        <a class="btn yellow" href="{esc(q)}">✏️ {esc(name)} 무료 상담 신청</a>
        <a class="btn white" href="tel:{gen.PHONE}">📞 {gen.PHONE}</a>
        <a class="btn white" href="https://map.naver.com/p/search/{esc(addr)}" target="_blank" rel="noopener">🗺️ 지도 보기</a>
      </div>
      <p class="muted small">* 지점 직통 번호는 연결이 어려운 경우가 많아요. 상담 신청이나 위 번호로 연락 주시면 {esc(name)}으로 연결해 드려요.</p>

      <h2>센터 정보</h2>
      <div class="compare card info-table"><table><tbody>{info_rows}</tbody></table></div>

      <h2>과목별 개설 학년</h2>
      <div class="compare card grade-table"><table>
        <thead><tr><th></th>{"".join(f"<th>{g}</th>" for g in GRADES)}</tr></thead>
        <tbody>{grade_rows}</tbody></table></div>
      <p class="muted small">* 개설 과목과 학년은 바뀔 수 있어요. 상담 때 확인해 주세요.</p>

      <h2>{esc(name)} 근처 학교</h2>
      <p>{esc(name)}에는 이 학교 학생들이 많이 다녀요. 학교를 누르면 학사일정과 시험 정보를 볼 수 있어요.</p>
      {school_html}
      {f'<p class="kind-label">근처 아파트</p><div class="school-links plain">{"".join(f"<span>{esc(a)}</span>" for a in apts)}</div>' if apts else ""}

      {'<h2>근처 학교 다가오는 시험</h2><div class="sch-list" id="exams"><p class="sch-msg">나이스에서 시험 일정을 불러오는 중…</p></div>' if exam_schools else ""}

      <h2>{esc(name)} 수업현황</h2>
      <div class="posts" id="branchPosts"></div>
      <p class="sch-msg" id="branchPostsEmpty" hidden>아직 {esc(name)} 수업현황 글이 없어요. <a href="/class-status.html" style="text-decoration:underline">다른 지점 글 보기</a></p>

      <h2>수강료 (한 달 기준)</h2>
      <div class="compare card"><table>
        <thead><tr><th></th><th>주 2회</th><th>주 3회</th><th>주 5회</th></tr></thead>
        <tbody>{price_rows}</tbody></table></div>
      <p class="muted small">* {'서울' if region == '서울' else '서울 외 지역'} 기준 참고용 금액이에요. 정확한 수강료는 지점 방문 상담 때 정해져요. <a href="/price.html">수강료 자세히</a></p>

      <h2>와와 둥지학습</h2>
      <p>코치 선생님을 가운데 두고 원형 테이블에 둘러앉아, 학생마다 다른 교재와 진도로 공부해요. 막히면 바로 질문하고, 학습 플래너로 계획과 실행을 함께 점검해요. <a href="/about.html#nest" style="text-decoration:underline">둥지학습 자세히 보기</a></p>

      <div class="next-cta" style="margin-top:36px">
        <a href="/centers.html" class="to-next"><small>다른 지점 보기 →</small><b>센터 찾기</b></a>
        <a href="{esc(q)}" class="to-apply"><small>{esc(name)} 상담 →</small><b>무료 상담 신청 ✏️</b></a>
      </div>
    </div>
  </section>

  <script src="/schedule.js"></script>
  <script src="/class-posts.js"></script>
  <script>
    (() => {{
      const esc = Schedule.esc;
      // 이 지점 수업현황 글
      const posts = (window.CLASS_POSTS || []).filter(p => p.branch === {json.dumps(name, ensure_ascii=False)}).slice(0, 6);
      document.getElementById('branchPosts').innerHTML = posts.map(p => `
        <a class="card post" href="/class/${{encodeURIComponent(p.slug)}}.html">
          <div class="thumb" style="${{p.thumb ? `background:center / cover no-repeat url('${{encodeURI(p.thumb)}}')` : ''}}">${{p.thumb ? '' : p.emoji}}</div>
          <div class="body"><span class="meta">${{p.date.replace(/-/g, '.')}}</span><h3>${{esc(p.title)}}</h3></div>
        </a>`).join('');
      document.getElementById('branchPostsEmpty').hidden = posts.length > 0;

      // 근처 학교 다가오는 시험 (나이스)
      const box = document.getElementById('exams');
      if (!box) return;
      const schools = {json.dumps(exam_schools[:10], ensure_ascii=False)};
      const ymd = d => `${{d.getFullYear()}}${{String(d.getMonth() + 1).padStart(2, '0')}}${{String(d.getDate()).padStart(2, '0')}}`;
      const from = new Date(), to = new Date(); to.setDate(to.getDate() + 75);
      const day = s => new Date(`${{s.slice(0, 4)}}-${{s.slice(4, 6)}}-${{s.slice(6, 8)}}`);
      Promise.all(schools.map(s => Schedule.neis('SchoolSchedule', {{ ATPT_OFCDC_SC_CODE: s.o, SD_SCHUL_CODE: s.c, AA_FROM_YMD: ymd(from), AA_TO_YMD: ymd(to) }})
        .then(rows => {{
          const ex = rows.filter(r => /중간|기말|(지필|정기)\\s*(고사|평가)/.test(r.EVENT_NM) && !/모의/.test(r.EVENT_NM)).map(r => r.AA_YMD).sort();
          return ex.length ? {{ ...s, start: ex[0], end: ex.filter(x => (day(x) - day(ex[0])) / 864e5 <= 7).pop() }} : null;
        }}).catch(() => null)))
        .then(list => {{
          list = list.filter(Boolean).sort((a, b) => a.start.localeCompare(b.start));
          const fmt = s => `${{+s.slice(4, 6)}}월 ${{+s.slice(6, 8)}}일`;
          box.innerHTML = list.length ? list.map(s => {{
            const dd = Math.ceil((day(s.start) - new Date(new Date().toDateString())) / 864e5);
            return `<a class="sch-ev ev-exam" href="${{s.u}}#sch"><span class="d">${{fmt(s.start)}}${{s.end !== s.start ? ' ~ ' + fmt(s.end) : ''}}</span><span class="n">📝 ${{esc(s.n)}} 시험 <b>D-${{dd}}</b></span></a>`;
          }}).join('') : '<p class="sch-msg">앞으로 두 달 안에 등록된 시험 일정이 없어요.</p>';
        }});
    }})();
  </script>
'''
    sch_txt = ", ".join(x.strip() for k in ("인근 중학교", "인근 고등학교") for x in info.get(k, "").split(",") if x.strip())[:80]
    title = f"와와학습코칭센터 {name} · {dong} {gu} 수학 · 영어 · 국어 학원 | 해피에듀"
    desc = f"와와학습코칭센터 {name}({addr}). {sch_txt} 등 근처 학교 학생들의 내신 · 자기주도학습 코칭. 과목별 개설 학년, 수강료, 상담 신청."
    gen.build(f"center/{name}.html", title, esc(desc), body, quiet=True)
    pages.append(center_url(name))

# 센터 찾기 카드: '지도 보기' → '자세히 보기'
cp = ROOT / "tools/pages/centers.html"
s = cp.read_text(encoding="utf-8")
def link(m):
    name = m.group(1)
    block = m.group(0)
    return re.sub(r'<a class="btn white" href="https://map\.naver\.com/p/search/[^"]*" target="_blank" rel="noopener">지도 보기</a>',
                  f'<a class="btn white" href="{center_url(html.unescape(name))}">자세히 보기</a>', block, count=1)
s2 = re.sub(r'<h3>와와 ([^<]+)</h3>.*?</article>', link, s, flags=re.S)
cp.write_text(s2, encoding="utf-8")

# 사이트맵
sm = ROOT / "sitemap.xml"
t = re.sub(r"  <url><loc>https://happyedu\.co\.kr/center/[^<]*</loc></url>\n", "", sm.read_text(encoding="utf-8"))
t = t.replace("</urlset>", "".join(f"  <url><loc>https://happyedu.co.kr{u}</loc></url>\n" for u in pages) + "</urlset>")
sm.write_text(t, encoding="utf-8", newline="\n")
print("지점 상세", len(pages), "/ 센터 찾기 카드 연결", s2.count("자세히 보기</a>"))
