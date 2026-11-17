"""수업현황(시험 대비 이야기) 글 생성
usage: python -I build_posts.py <gen.py 폴더> <데이터 폴더> <작성일 YYYY-MM-DD> <글 개수>
- 와와 지점 근처 중 · 고등학교 중 나이스에 기말고사 일정이 있는 학교를 지점마다 하나씩 골라 글을 만든다.
- 이미 만든 글(class-posts.json)은 유지하고 새 글만 맨 앞에 추가한다.
"""
import json, sys, html, pathlib, datetime, urllib.parse, collections

GEN_DIR, DATA, TODAY, N = sys.argv[1], pathlib.Path(sys.argv[2]), datetime.date.fromisoformat(sys.argv[3]), int(sys.argv[4])
sys.path.insert(0, GEN_DIR)
import gen

esc = lambda s: html.escape(str(s), quote=True)
W = "월화수목금토일"
def d(s): return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
def fmt(x): return f"{x.month}월 {x.day}일({W[x.weekday()]})"

# ---------- 과목별 공부법 (중 · 고) ----------
METHODS = {
 ("수학", "중"): dict(
   emoji="📐", hook="풀 때는 아는 것 같은데 시험에서 또 틀린다면",
   title="틀린 문제에 '틀린 이유 한 줄'을 붙여 봅니다",
   lead="수학 오답은 다시 풀기만 해서는 잘 줄지 않아요. 왜 틀렸는지를 먼저 이름 붙이면, 같은 실수가 어디서 반복되는지 보이기 시작합니다.",
   steps=[("이유 분류", "틀린 문제마다 '계산 실수 · 개념 헷갈림 · 문제를 잘못 읽음' 중 하나를 옆에 적어요."),
          ("유형별 다시 풀기", "같은 이유끼리 모아 다시 풀면, 내가 약한 단원과 습관이 한눈에 보여요."),
          ("빈 종이 풀이", "시험 1주 전에는 해설 없이 빈 종이에 풀이 과정을 처음부터 끝까지 써 봐요.")]),
 ("수학", "고"): dict(
   emoji="📈", hook="문제집은 많이 풀었는데 학교 시험 점수가 그대로라면",
   title="학교 프린트 예제의 숫자를 바꿔서 다시 풀어 봅니다",
   lead="고등 내신 수학은 선생님이 수업 시간에 강조한 예제가 모양을 바꿔 나오는 경우가 많아요. 새 문제집보다 수업 자료를 깊게 파는 쪽이 효율적일 때가 많습니다.",
   steps=[("수업 자료 모으기", "교과서 예제, 학교 프린트, 수업 필기를 시험 범위 순서대로 한곳에 모아요."),
          ("숫자 · 조건 바꾸기", "예제의 숫자나 조건을 하나씩 바꿔 풀면서 풀이가 어떻게 달라지는지 확인해요."),
          ("서술형 과정 쓰기", "답만 맞히지 말고 채점자가 읽을 수 있게 풀이 과정을 문장으로 정리해요.")]),
 ("영어", "중"): dict(
   emoji="🔤", hook="본문은 외웠는데 서술형 영작에서 점수가 깎인다면",
   title="본문 문장을 '끊어 읽기'로 나누고 조건 영작을 연습합니다",
   lead="중학교 영어 내신은 교과서 본문에서 대부분 나와요. 통째로 외우기보다 문장 구조를 이해하면, 단어 순서를 바꾸는 서술형에도 흔들리지 않습니다.",
   steps=[("끊어 읽기 표시", "본문 문장마다 주어 / 동사 / 나머지에 빗금을 쳐서 구조를 눈으로 확인해요."),
          ("빈칸 셀프 테스트", "본문을 복사해 핵심 단어와 문법 자리를 지우고 채워 보며 외워요."),
          ("조건 영작", "'주어진 단어를 모두 사용, 7단어' 같은 조건을 직접 만들어 문장을 써 봐요.")]),
 ("영어", "고"): dict(
   emoji="📚", hook="지문 내용은 아는데 변형 문제에서 시간이 부족하다면",
   title="지문마다 '핵심 문장 하나'와 어법 포인트를 표시해 둡니다",
   lead="고등 영어 내신은 수업한 지문을 순서 · 삽입 · 어법 문제로 바꿔 내는 경우가 많아요. 지문을 다시 읽는 대신, 지문마다 무엇을 봐야 하는지 정리해 두면 시간이 줄어듭니다.",
   steps=[("핵심 문장 표시", "지문마다 주제를 담은 문장 하나에 밑줄을 긋고, 우리말로 한 줄 요약해요."),
          ("어법 포인트", "수일치 · 시제 · 관계사처럼 문제로 나오기 쉬운 자리에 동그라미를 쳐 둬요."),
          ("순서 · 삽입 연습", "문단을 잘라 섞은 뒤 연결어와 지시어를 근거로 다시 맞춰 봐요.")]),
 ("국어", "중"): dict(
   emoji="📖", hook="아는 내용인데 서술형에서 부분 점수만 받는다면",
   title="서술형 조건에 번호를 붙이고, 조건부터 답안에 넣습니다",
   lead="국어 서술형은 내용보다 조건을 놓쳐서 감점되는 경우가 많아요. 답을 쓰기 전에 조건을 쪼개 두면 빠뜨리는 일이 줄어듭니다.",
   steps=[("조건 번호 매기기", "'두 문장으로, ~을 포함하여'처럼 문제의 조건마다 ①②③ 번호를 붙여요."),
          ("핵심어 먼저", "답에 꼭 들어가야 할 단어를 먼저 적고, 그 단어로 뼈대 문장을 만들어요."),
          ("조건 확인", "다 쓴 뒤 번호를 하나씩 지우면서 조건을 모두 지켰는지 확인해요.")]),
 ("국어", "고"): dict(
   emoji="✒️", hook="작품은 읽었는데 문제에서 화자의 정서를 자꾸 틀린다면",
   title="문학 작품마다 '화자 · 정서 · 표현' 표를 한 장씩 만듭니다",
   lead="고등 국어 내신 문학은 같은 작품을 여러 각도에서 물어봐요. 작품마다 핵심 정보를 같은 틀로 정리해 두면 비교 문제에도 대비할 수 있습니다.",
   steps=[("표 만들기", "작품마다 화자(서술자), 상황, 정서 · 태도, 표현법, 주제를 한 장에 정리해요."),
          ("근거 구절 연결", "정서를 적을 때는 그렇게 판단한 구절을 꼭 옆에 옮겨 적어요."),
          ("작품끼리 비교", "범위 안 작품들을 나란히 놓고 공통점 · 차이점을 한 줄씩 써 봐요.")]),
 ("과학", "중"): dict(
   emoji="🔬", hook="개념은 외웠는데 그래프 · 실험 문항에서 막힌다면",
   title="그래프는 '제목 → 축 → 변화' 순서로 읽고 변인에 표시합니다",
   lead="중학교 과학 시험의 자료 문항은 읽는 순서만 정해 두어도 훨씬 쉬워져요. 실험 문항은 무엇을 바꾸고 무엇을 같게 했는지가 핵심입니다.",
   steps=[("그래프 읽는 순서", "제목 → 가로축 · 세로축 → 값이 어떻게 변하는지 순서로 한 줄씩 말해 봐요."),
          ("변인 표시", "실험 문항에서 다르게 한 조건(조작 변인)과 같게 한 조건(통제 변인)에 다른 색으로 표시해요."),
          ("개념 서술", "결과를 설명할 때 교과서 개념어를 넣어 두 문장으로 써 봐요.")]),
 ("과학", "고"): dict(
   emoji="🧪", hook="단원마다 따로 외워서 통합 문제가 어렵다면",
   title="단원끼리 이어지는 '개념 연결 지도'를 그려 봅니다",
   lead="고등 과학 내신은 여러 개념을 섞어 묻는 문항이 많아요. 개념을 낱개로 외우기보다 서로 어떻게 이어지는지 그려 두면 응용 문제에 강해집니다.",
   steps=[("핵심 개념 뽑기", "시험 범위에서 꼭 알아야 할 개념을 10개 안팎으로 뽑아요."),
          ("연결선 긋기", "개념 사이에 '때문에 · 그래서 · 반대로' 같은 말로 화살표를 이어요."),
          ("계산 문항 점검", "계산 문제는 단위와 유효숫자를 마지막에 한 번 더 확인하는 습관을 들여요.")]),
 ("사회", "중"): dict(
   emoji="🌏", hook="교과서 지도 · 자료는 여러 번 봤는데 문제에서 막힌다면",
   title="자료는 직접 다시 그려 보고, 비슷한 개념은 비교표로 정리합니다",
   lead="중학교 사회는 지도 · 그래프 · 통계 자료를 해석하는 문항이 많아요. 눈으로 보는 것과 손으로 그려 보는 것은 기억에 남는 정도가 다릅니다.",
   steps=[("따라 그리기", "교과서 핵심 지도나 그래프를 한 번 따라 그리며 특징을 적어요."),
          ("덮고 그리기", "책을 덮고 다시 그려 본 뒤, 빠진 부분을 다른 색으로 채워요."),
          ("비교표", "헷갈리는 개념은 두 칸 표로 나란히 놓고 차이를 한 줄씩 정리해요.")]),
 ("한국사", "고"): dict(
   emoji="🏛️", hook="사건은 외웠는데 순서 · 인과 문제에서 틀린다면",
   title="연표 위에 '원인 → 사건 → 결과' 카드를 붙여 흐름을 잡습니다",
   lead="한국사 내신은 사건의 순서와 앞뒤 관계를 묻는 문항이 많아요. 사건을 낱개로 외우기보다 흐름 위에 놓으면 오래 기억됩니다.",
   steps=[("연표 그리기", "시험 범위 시대를 한 줄 연표로 그리고 주요 사건을 순서대로 올려요."),
          ("인과 카드", "사건마다 원인 · 결과를 한 줄씩 적은 작은 카드를 만들어 연표에 붙여요."),
          ("순서 퀴즈", "카드를 섞은 뒤 순서대로 다시 놓아 보며 흐름을 점검해요.")]),
}
ROTATION = {"중": ["수학", "영어", "국어", "과학", "사회"], "고": ["수학", "영어", "국어", "과학", "한국사"]}

def short(name):
    for a, b in (("여자고등학교", "여고"), ("여자중학교", "여중"), ("고등학교", "고"), ("중학교", "중")):
        if name.endswith(a): return name[: -len(a)] + b
    return name

# ---------- 학교 고르기 ----------
matched = json.loads((DATA / "schools_matched.json").read_text(encoding="utf-8"))
exams = json.loads((DATA / "exam_dates.json").read_text(encoding="utf-8"))
posts_p = pathlib.Path(gen.OUT, "class-posts.json")
posts = json.loads(posts_p.read_text(encoding="utf-8")) if posts_p.exists() else []
done_schools = {p["code"] for p in posts}
used_centers = collections.Counter(p["branch"] for p in posts)

cands = []
for code, ev in exams.items():
    if code in done_schools or code not in matched: continue
    days = sorted({x[0] for x in ev})
    start = d(days[0])
    if (start - TODAY).days < 10: continue            # 너무 임박한 시험은 제외
    # 첫 시험일부터 이어지는 날만 시험 기간으로
    block = [days[0]]
    for x in days[1:]:
        if (d(x) - d(block[-1])).days <= 4: block.append(x)
        else: break
    s = matched[code]
    cands.append((start, code, s, block, ev[0][1]))
cands.sort(key=lambda c: c[0])

new, centers_seen, region_n = [], set(), collections.Counter()
for start, code, s, block, ev_name in cands:
    c = s["centers"][0]
    if c["center"] in centers_seen or used_centers[c["center"]]: continue
    if region_n[c["region"]] >= max(3, N // 5): continue
    centers_seen.add(c["center"]); region_n[c["region"]] += 1
    lv = "중" if s["SCHUL_KND_SC_NM"] == "중학교" else "고"
    subj = ROTATION[lv][(len(posts) + len(new)) % 5]
    new.append(dict(start=start, code=code, s=s, block=block, ev=ev_name, c=c, lv=lv, subj=subj))
    if len(new) >= N: break

# ---------- 글 페이지 ----------
def build_post(p):
    s, c, m = p["s"], p["c"], METHODS[(p["subj"], p["lv"])]
    sh, start, end = short(s["SCHUL_NM"]), d(p["block"][0]), d(p["block"][-1])
    dday = (start - TODAY).days
    period = fmt(start) if start == end else f"{fmt(start)} ~ {fmt(end)}"
    grade_note = ""
    if "(" in p["ev"] and "학년" in p["ev"]:
        grade_note = f' <span class="muted">({esc(p["ev"].split("(", 1)[1].rstrip(")"))} 기준)</span>'
    area = s["ORG_RDNMA"].split()[1] if len(s["ORG_RDNMA"].split()) > 1 else c["region"]
    slug = f'{TODAY.isoformat()}-{s["SD_SCHUL_CODE"]}-{p["subj"]}'
    title = f'{sh} {p["subj"]} 기말 D-{dday} · {m["title"]} ({c["center"]})'
    excerpt = f'{m["hook"]}, {m["title"].rstrip("다").rstrip("니")}… {sh} 2학기 기말고사({period})까지 남은 기간에 맞춘 {p["subj"]} 준비법과 주차별 계획을 정리했어요.'
    excerpt = f'{m["hook"]}? {sh} 2학기 기말고사({period})에 맞춰 {p["subj"]} 준비 방법과 주차별 계획을 정리했어요.'

    # 시험일에서 거꾸로 주차 계획
    weeks = []
    plan = [("범위 확인 · 개념 정리", "시험 범위와 수행평가 일정을 확인하고, 교과서 개념을 내 말로 정리해요."),
            ("문제 풀이 · 오답 정리", "범위 문제를 풀고 틀린 문제에 이유를 붙여 오답 노트에 모아요."),
            ("학교 자료 집중", "학교 프린트 · 수업 필기 · 교과서 예제 위주로 다시 보며 출제 포인트를 잡아요."),
            ("실전 점검", "시간을 재고 풀어 보고, 빈 종이 테스트로 마지막 빈틈을 확인해요.")]
    for i in range(4, 0, -1):
        w_end = start - datetime.timedelta(days=7 * (i - 1) + 1)
        w_start = start - datetime.timedelta(days=7 * i)
        if w_end < TODAY: continue
        w_start = max(w_start, TODAY)
        weeks.append((f"{fmt(w_start)} ~ {fmt(w_end)}", *plan[4 - i]))
    weeks_html = "".join(f'<div class="flow-item"><div class="dot">{n}</div><div class="card"><h3>{esc(t)} <small class="muted">{esc(r)}</small></h3><p>{esc(x)}</p></div></div>'
                         for n, (r, t, x) in enumerate(weeks, 1))
    steps_html = "".join(f'<li><b>{esc(a)}</b> — {esc(b)}</li>' for a, b in m["steps"])
    school_url = "/" + urllib.parse.quote(f'school/{s["SCHUL_NM"]}.html')
    q = lambda **kw: "/contact.html?" + urllib.parse.urlencode(kw) + "#apply"

    body = gen.page_hero(f'{m["emoji"]} {esc(c["center"])}', f'<a href="/class-status.html">수업현황</a> › {esc(area)}',
                         f'{esc(sh)} {esc(p["subj"])} 기말 D-{dday}<br><span class="sub-h1">{esc(m["title"])}</span>',
                         f'{esc(TODAY.year)}.{TODAY.month:02d}.{TODAY.day:02d} · 와와 {esc(c["center"])} · {esc(s["SCHUL_NM"])}') + f'''
  <article class="block post-body">
    <div class="wrap narrow">
      <div class="card exam-card">
        <div><span class="muted">{esc(s["SCHUL_NM"])} 2학기 기말고사</span><b>{period}</b>{grade_note}</div>
        <div class="dday">D-{dday}</div>
      </div>
      <p class="muted small">* {TODAY.month}월 {TODAY.day}일 기준 나이스 학사일정이에요. 시험 범위와 과목별 날짜는 학교 공지로 꼭 확인해 주세요. <a href="{school_url}#sch">{esc(sh)} 전체 학사일정 보기</a></p>

      <h2>{esc(m["hook"])}</h2>
      <p>{esc(m["lead"])}</p>
      <h2>{esc(p["subj"])}, 이렇게 준비해요</h2>
      <ul class="checklist">{steps_html}</ul>

      <h2>시험까지 {len(weeks)}주 계획</h2>
      <p>{esc(sh)} 기말고사 첫날({fmt(start)})에서 거꾸로 계산한 주차별 계획이에요.</p>
      <div class="flow">{weeks_html}</div>

      <h2>와와 둥지 교실에서는</h2>
      <p>와와학습코칭센터에서는 학생마다 시험 날짜와 범위가 달라서, 학교별 일정에 맞춰 각자 학습 플래너를 세워요. 코치 선생님 한 분이 여러 학생을 맡되 학생마다 다른 진도로 지도하고, 틀린 문제는 이유를 붙여 다시 풀게 해서 같은 실수를 줄이는 데 집중해요.</p>

      <h2>{esc(sh)} 근처 와와 {esc(c["center"])}</h2>
      <div class="card center">
        <h3>와와 {esc(c["center"])}</h3>
        <p class="addr">📍 {esc(c["addr"])}</p>
        <div class="center-btns">
          <a class="btn white" href="https://map.naver.com/p/search/{esc(c["addr"])}" target="_blank" rel="noopener">지도 보기</a>
          <a class="btn yellow" href="{esc(q(center=c["center"], region=c["region"], school=s["SCHUL_NM"], subject=p["subj"] if p["subj"] != "한국사" else "한국사"))}">시험 대비 상담 신청</a>
        </div>
      </div>
      <p class="post-links"><a href="{school_url}">🏫 {esc(s["SCHUL_NM"])} 학원 · 과외 · 학사일정</a> <a href="/class-status.html">📋 다른 수업현황 글 보기</a></p>
    </div>
  </article>
'''
    gen.build(f"class/{slug}.html", f"{title} | 해피에듀",
              esc(f'{s["SCHUL_NM"]} {p["subj"]} 2학기 기말고사({period}) 대비. {m["hook"]}? {m["title"]}. 와와학습코칭센터 {c["center"]}.'), body, quiet=True)
    return dict(slug=slug, code=s["SD_SCHUL_CODE"], region=c["region"], area=area, branch=c["center"], school=s["SCHUL_NM"],
                subject=p["subj"], date=TODAY.isoformat(), emoji=m["emoji"], title=title, excerpt=excerpt)

entries = [build_post(p) for p in new]
posts = entries + posts
posts_p.write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
pathlib.Path(gen.OUT, "class-posts.js").write_text(
    "// 수업현황 글 목록 (build_posts.py가 만듦, 최신이 위)\nwindow.CLASS_POSTS = " + json.dumps(posts, ensure_ascii=False) + ";\n", encoding="utf-8")
print("new posts", len(entries), "total", len(posts))
for e in entries: print(" ", e["region"], e["branch"], e["school"], e["subject"], e["title"][:40])
