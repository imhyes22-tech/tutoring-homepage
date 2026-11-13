// 나이스 교육정보 개방 포털 학사일정 (학사일정 페이지 · 학교별 페이지 공용)
// 인증키: open.neis.go.kr → 인증키 신청. 비어 있으면 일정이 5개까지만 나와요.
const NEIS_KEY = '';

const Schedule = (() => {
  const API = 'https://open.neis.go.kr/hub/';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, ch => '&#' + ch.charCodeAt(0) + ';');
  const ymd = d => `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
  const pretty = s => `${+s.slice(4, 6)}월 ${+s.slice(6, 8)}일 (${'일월화수목금토'[new Date(`${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`).getDay()]})`;
  const ICON = { exam: '📝', break: '🏖️', off: '😴', etc: '📌' };
  const GRADE_KEYS = ['ONE', 'TW', 'THREE', 'FR', 'FIV', 'SIX'];

  async function neis(service, params) {
    const q = new URLSearchParams({ Type: 'json', pIndex: 1, pSize: NEIS_KEY ? 1000 : 100, ...params });
    if (NEIS_KEY) q.set('KEY', NEIS_KEY);
    const data = await (await fetch(API + service + '?' + q)).json();
    return data[service] ? data[service][1].row : [];
  }

  function kind(ev) {
    const n = ev.EVENT_NM;
    if (/고사|시험|평가|수능|모의/.test(n)) return 'exam';
    if (/방학|개학|종업|졸업|입학/.test(n)) return 'break';
    if (ev.SBTR_DD_SC_NM === '휴업일' || /휴업|휴일|대체/.test(n)) return 'off';
    return 'etc';
  }

  // school: { ATPT_OFCDC_SC_CODE, SD_SCHUL_CODE, SCHUL_KND_SC_NM }
  // els: { grades, list } 요소
  async function show(school, els) {
    const from = new Date(), to = new Date();
    to.setMonth(to.getMonth() + 6);
    const rows = (await neis('SchoolSchedule', {
      ATPT_OFCDC_SC_CODE: school.ATPT_OFCDC_SC_CODE, SD_SCHUL_CODE: school.SD_SCHUL_CODE,
      AA_FROM_YMD: ymd(from), AA_TO_YMD: ymd(to),
    })).filter(r => r.EVENT_NM !== '토요휴업일');

    const grades = school.SCHUL_KND_SC_NM === '초등학교' ? 6 : 3;
    let grade = 0;
    els.grades.innerHTML = ['전체', ...Array.from({ length: grades }, (_, i) => `${i + 1}학년`)]
      .map((g, i) => `<button data-g="${i}"${i === 0 ? ' class="on"' : ''}>${g}</button>`).join('');
    els.grades.onclick = ev => {
      const b = ev.target.closest('button'); if (!b) return;
      els.grades.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
      grade = +b.dataset.g; draw();
    };

    function draw() {
      const list = rows.filter(r => !grade || r[GRADE_KEYS[grade - 1] + '_GRADE_EVENT_YN'] !== 'N');
      if (!list.length) { els.list.innerHTML = '<p class="sch-msg">앞으로 6개월 동안 등록된 일정이 없어요.</p>'; return; }
      let month = '';
      els.list.innerHTML = list.map(r => {
        const m = `${r.AA_YMD.slice(0, 4)}년 ${+r.AA_YMD.slice(4, 6)}월`;
        const head = m !== month ? `<h3 class="sch-month">${(month = m)}</h3>` : '';
        const k = kind(r);
        return `${head}<div class="sch-ev ev-${k}"><span class="d">${pretty(r.AA_YMD)}</span><span class="n">${ICON[k]} ${esc(r.EVENT_NM)}</span></div>`;
      }).join('');
      if (!NEIS_KEY) els.list.insertAdjacentHTML('beforeend', '<p class="note">* 지금은 미리보기라 일부 일정만 보여요.</p>');
    }
    draw();
  }

  return { neis, show, esc };
})();
