"""수업현황 자동 글 쓰기 (GitHub Actions에서 매일 아침 실행)

와와 지점 근처 중 · 고등학교 중 나이스 학사일정에
  - 10~45일 뒤 시험(중간 · 기말)이 있으면 → 시험 대비 글
  - 없고 7~40일 뒤 방학이 시작되면       → 방학 계획 글
을 하나 골라 content/class/{날짜}-{학교코드}-{종류}.md 로 저장한다.
같은 학교는 한 번만, 최근에 쓴 지점은 피한다. 지어낸 학생 이야기나 성적 사례는 쓰지 않는다.

usage: python tools/auto_post.py [글 개수=1] [날짜 YYYY-MM-DD]
"""
import json, re, sys, random, pathlib, datetime, urllib.request, urllib.parse, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from post_methods import METHODS, ROTATION
from build_cms import parse_front, dump_front

COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 1
TODAY = (datetime.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2
         else (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).date())   # 한국 시간
KEY = re.search(r"NEIS_KEY = '([0-9a-f]+)'", (ROOT / "schedule.js").read_text(encoding="utf-8")).group(1)
COVERS = sorted(p.name for p in (ROOT / "images" / "class").glob("wawa-*.jpg"))
CONTENT = ROOT / "content" / "class"
W = "월화수목금토일"
esc = lambda s: html.escape(str(s), quote=True)

def d(s): return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
def fmt(x): return f"{x.month}월 {x.day}일({W[x.weekday()]})"
def ymd(x): return x.strftime("%Y%m%d")

def short(name):
    for a, b in (("여자고등학교", "여고"), ("여자중학교", "여중"), ("고등학교", "고"), ("중학교", "중")):
        if name.endswith(a): return name[: -len(a)] + b
    return name

def schedule(s, start, end):
    url = "https://open.neis.go.kr/hub/SchoolSchedule?" + urllib.parse.urlencode({
        "KEY": KEY, "Type": "json", "pSize": 500, "ATPT_OFCDC_SC_CODE": s["ATPT_OFCDC_SC_CODE"],
        "SD_SCHUL_CODE": s["SD_SCHUL_CODE"], "AA_FROM_YMD": ymd(start), "AA_TO_YMD": ymd(end)})
    try:
        data = json.load(urllib.request.urlopen(url, timeout=20))
    except Exception:
        return []
    return data["SchoolSchedule"][1]["row"] if "SchoolSchedule" in data else []

def first_block(rows, test):
    days = sorted({r["AA_YMD"] for r in rows if test(r["EVENT_NM"])})
    if not days: return None, None
    block = [days[0]]
    for x in days[1:]:
        if (d(x) - d(block[-1])).days <= 4: block.append(x)
        else: break
    name = next(r["EVENT_NM"] for r in rows if r["AA_YMD"] == days[0] and test(r["EVENT_NM"]))
    return block, name

is_exam = lambda n: re.search(r"중간|기말|(지필|정기)\s*(고사|평가)", n) and "모의" not in n
is_break = lambda n: re.search(r"(여름|겨울)\s*방학", n) and "방학식" not in n


# ---------- 이미 쓴 글 ----------
existing = []
for f in CONTENT.glob("*.md"):
    meta, _ = parse_front(f.read_text(encoding="utf-8"))
    code = meta.get("code") or (f.stem.split("-")[3] if len(f.stem.split("-")) > 3 else "")
    existing.append(dict(code=str(code), branch=meta.get("branch", ""), date=str(meta.get("date", ""))))
used_codes = {e["code"] for e in existing}
recent = sorted(existing, key=lambda e: e["date"], reverse=True)
recent_branches = {e["branch"] for e in recent[:40]}
n_posts = len(existing)

matched = json.loads((ROOT / "tools" / "data" / "schools_matched.json").read_text(encoding="utf-8"))
cands = [s for s in matched.values() if s["SCHUL_KND_SC_NM"] in ("중학교", "고등학교") and s["SD_SCHUL_CODE"] not in used_codes]
random.seed(TODAY.isoformat())
random.shuffle(cands)
cands.sort(key=lambda s: s["centers"][0]["center"] in recent_branches)     # 최근에 안 쓴 지점 먼저


def write_post(s, kind, block, ev_name):
    global n_posts
    c, lv = s["centers"][0], ("중" if s["SCHUL_KND_SC_NM"] == "중학교" else "고")
    sh, start, end = short(s["SCHUL_NM"]), d(block[0]), d(block[-1])
    dday = (start - TODAY).days
    period = fmt(start) if start == end else f"{fmt(start)} ~ {fmt(end)}"
    area = s["ORG_RDNMA"].split()[1] if len(s["ORG_RDNMA"].split()) > 1 else c["region"]
    sem = "1학기" if start.month <= 8 else "2학기"
    grade_note = ""
    if "(" in ev_name and "학년" in ev_name:
        grade_note = f' <span class="muted">({esc(ev_name.split("(", 1)[1].rstrip(")"))} 기준)</span>'
    school_url = "/school/" + urllib.parse.quote(s["SCHUL_NM"]) + ".html"
    note = (f'<p class="muted small">* {TODAY.month}월 {TODAY.day}일 기준 나이스 학사일정이에요. 학교 사정에 따라 바뀔 수 있으니 학교 공지로 꼭 확인해 주세요. '
            f'<a href="{school_url}#sch">{esc(sh)} 전체 학사일정 보기</a></p>')
    coaching = ('<h2>와와 둥지 교실에서는</h2><p>와와학습코칭센터에서는 학생마다 학교 일정과 진도가 달라서, 각자 학습 플래너를 세우고 '
                '수업 때마다 실행했는지 함께 점검해요. 코치 선생님 한 분이 여러 학생을 맡되 학생마다 다른 진도로 지도하고, '
                '틀린 문제는 이유를 붙여 다시 풀게 해서 같은 실수를 줄이는 데 집중해요.</p>')

    if kind == "exam":
        subj = ROTATION[lv][n_posts % 5]
        m = METHODS[(subj, lv)]
        exam = "중간고사" if "중간" in ev_name else ("기말고사" if "기말" in ev_name else "정기고사")
        weeks, plan = [], [("범위 확인 · 개념 정리", "시험 범위와 수행평가 일정을 확인하고, 교과서 개념을 내 말로 정리해요."),
                           ("문제 풀이 · 오답 정리", "범위 문제를 풀고 틀린 문제에 이유를 붙여 오답 노트에 모아요."),
                           ("학교 자료 집중", "학교 프린트 · 수업 필기 · 교과서 예제 위주로 다시 보며 출제 포인트를 잡아요."),
                           ("실전 점검", "시간을 재고 풀어 보고, 빈 종이 테스트로 마지막 빈틈을 확인해요.")]
        for i in range(4, 0, -1):
            w_end, w_start = start - datetime.timedelta(days=7 * (i - 1) + 1), start - datetime.timedelta(days=7 * i)
            if w_end < TODAY: continue
            weeks.append((f"{fmt(max(w_start, TODAY))} ~ {fmt(w_end)}", *plan[4 - i]))
        title = f'{sh} {subj} {exam[:2]} D-{dday} · {m["title"]} ({c["center"]})'
        excerpt = f'{m["hook"]}? {sh} {sem} {exam}({period})에 맞춰 {subj} 준비 방법과 주차별 계획을 정리했어요.'
        steps = "".join(f'<li><b>{esc(a)}</b> — {esc(b)}</li>' for a, b in m["steps"])
        body = (f'<div class="card exam-card"><div><span class="muted">{esc(s["SCHUL_NM"])} {sem} {exam}</span><b>{period}</b>{grade_note}</div><div class="dday">D-{dday}</div></div>\n'
                f'{note}\n<h2>{esc(m["hook"])}</h2>\n<p>{esc(m["lead"])}</p>\n<h2>{esc(subj)}, 이렇게 준비해요</h2>\n<ul class="checklist">{steps}</ul>\n'
                f'<h2>시험까지 {len(weeks)}주 계획</h2>\n<p>{esc(sh)} {exam} 첫날({fmt(start)})에서 거꾸로 계산한 주차별 계획이에요.</p>\n<div class="flow">'
                + "".join(f'<div class="flow-item"><div class="dot">{n}</div><div class="card"><h3>{esc(t)} <small class="muted">{esc(r)}</small></h3><p>{esc(x)}</p></div></div>'
                          for n, (r, t, x) in enumerate(weeks, 1)) + f'</div>\n{coaching}\n')
        emoji, slug_kind = m["emoji"], subj
    else:
        season = "겨울방학" if "겨울" in ev_name else "여름방학"
        subj = "방학 계획"
        nxt = "새 학년" if season == "겨울방학" else "2학기"
        title = f'{sh} {season} D-{dday} · 방학 첫 주에 정할 세 가지, {nxt} 준비는 여기서 갈립니다 ({c["center"]})'
        excerpt = f'{sh} {season}({fmt(start)} 시작)이 다가와요. 방학 동안 무엇을 복습하고 무엇을 예습할지, 하루 공부 시간을 어떻게 지킬지 정리했어요.'
        plan = [("1주차 · 지난 학기 정리", "틀린 문제와 약한 단원을 목록으로 만들고, 우선순위를 정해요."),
                ("2주차 · 약한 단원 복습", "목록 위쪽부터 개념을 다시 보고, 같은 유형을 다시 풀어요."),
                ("3주차 · 다음 학기 예습", f"{nxt} 첫 단원을 미리 읽고 모르는 용어를 표시해요."),
                ("4주차 · 습관 점검", "개학 1주 전에는 학기 중 일과에 맞춰 일어나고 공부하는 시간을 맞춰요.")]
        body = (f'<div class="card exam-card"><div><span class="muted">{esc(s["SCHUL_NM"])} {season} 시작</span><b>{fmt(start)}</b>{grade_note}</div><div class="dday">D-{dday}</div></div>\n'
                f'{note}\n<h2>방학은 길어 보여도 금방 지나가요</h2>\n<p>방학 계획이 흐지부지되는 가장 큰 이유는 "무엇을" 할지보다 "언제" 할지를 정하지 않아서예요. '
                f'방학이 시작되기 전에 아래 세 가지만 정해 두면 {nxt} 준비가 훨씬 수월해져요.</p>\n'
                '<ul class="checklist"><li><b>매일 공부 시작 시간</b> — 늦잠을 자도 공부 시작 시간은 하나로 정해요.</li>'
                '<li><b>복습할 단원 목록</b> — 지난 학기 시험지와 오답을 보고 다시 볼 단원을 적어요.</li>'
                f'<li><b>예습 범위</b> — {nxt} 교과서 앞부분 1~2단원까지만 욕심내지 않고 정해요.</li></ul>\n'
                f'<h2>방학 4주, 이렇게 나눠요</h2>\n<div class="flow">'
                + "".join(f'<div class="flow-item"><div class="dot">{n}</div><div class="card"><h3>{esc(t)}</h3><p>{esc(x)}</p></div></div>'
                          for n, (t, x) in enumerate(plan, 1)) + f'</div>\n{coaching}\n')
        emoji, slug_kind = ("☃️" if season == "겨울방학" else "☀️"), "방학"

    slug = f"{TODAY.isoformat()}-{s['SD_SCHUL_CODE']}-{slug_kind}"
    meta = dict(title=title, date=TODAY.isoformat(), branch=c["center"], subject=subj, school=s["SCHUL_NM"], area=area,
                emoji=emoji, excerpt=excerpt, photos=[], cover=f"/images/class/{COVERS[n_posts % len(COVERS)]}" if COVERS else "",
                code=s["SD_SCHUL_CODE"], published=True)
    (CONTENT / f"{slug}.md").write_text(dump_front(meta, body), encoding="utf-8", newline="\n")
    n_posts += 1
    print("새 글:", title)


made, tried = 0, 0
for s in cands:
    if made >= COUNT or tried >= 120: break
    tried += 1
    rows = schedule(s, TODAY + datetime.timedelta(days=1), TODAY + datetime.timedelta(days=60))
    block, name = first_block(rows, is_exam)
    if block and 10 <= (d(block[0]) - TODAY).days <= 45:
        write_post(s, "exam", block, name); made += 1; continue
    block, name = first_block(rows, is_break)
    if block and 7 <= (d(block[0]) - TODAY).days <= 40:
        write_post(s, "break", block, name); made += 1
print(f"자동 글 {made}개 (학교 {tried}곳 확인)")
