// 상담 신청을 받을 주소 (Formspree 등). 비어 있으면 신청이 전송되지 않아요.
const FORM_ENDPOINT = '';

// 모바일 메뉴 열고 닫기
const menu = document.getElementById('menu');
document.querySelector('.menu-toggle').addEventListener('click', () => menu.classList.toggle('open'));
menu.querySelectorAll('a').forEach(a => a.addEventListener('click', () => menu.classList.remove('open')));

// 지금 보고 있는 페이지 메뉴 강조
const here = location.pathname.split('/').pop() || 'index.html';
menu.querySelectorAll('a').forEach(a => {
  if (a.getAttribute('href').split('#')[0].replace(/^\//, '') === here) a.classList.add('on');
});

// 수강료: 서울 / 서울 외 전환
document.querySelectorAll('.toggle button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.toggle button').forEach(b => b.classList.remove('on'));
    btn.classList.add('on');
    const r = btn.dataset.r;
    document.querySelectorAll('.price b').forEach(b => {
      b.innerHTML = b.dataset[r] + '<small>만원</small>';
    });
  });
});

// 상담 신청서
const form = document.getElementById('applyForm');
if (form) {
  // 센터 찾기에서 넘어오면 지역 · 지점 미리 채우기
  const params = new URLSearchParams(location.search);
  if (params.get('center')) form.희망지점.value = '와와 ' + params.get('center');
  if (params.get('region')) form.시도.value = params.get('region');
  if (params.get('school')) form.학교.value = params.get('school');
  if (params.get('type') === 'tutor') form.querySelector('input[name="희망수업"][value="1:1 과외 (방문)"]').checked = true;

  const msg = document.getElementById('formMsg');
  const showMsg = (type, text) => { msg.className = 'form-msg ' + type; msg.textContent = text; };

  form.addEventListener('submit', async e => {
    e.preventDefault();
    msg.className = 'form-msg';

    const phone = form.연락처.value.replace(/[^0-9]/g, '');
    if (!form.학년.value || !form.시도.value || !form.상세지역.value.trim()) {
      return showMsg('err', '학년과 지역을 모두 입력해 주세요.');
    }
    if (!/^01[016789][0-9]{7,8}$/.test(phone)) {
      return showMsg('err', '연락처를 정확히 입력해 주세요. (예: 010-1234-5678)');
    }
    if (!form.개인정보동의.checked) {
      return showMsg('err', '개인정보 수집 · 이용 및 제3자 제공에 동의해 주세요.');
    }
    if (!FORM_ENDPOINT) {
      return showMsg('err', '온라인 접수 준비 중이에요. 010-8241-2051로 전화 주시면 바로 상담해 드려요.');
    }

    const data = new FormData(form);
    data.set('과목', data.getAll('과목').join(', ') || '미선택');
    const btn = form.querySelector('button[type=submit]');
    btn.disabled = true;
    try {
      const res = await fetch(FORM_ENDPOINT, { method: 'POST', body: data, headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error(res.status);
      form.reset();
      showMsg('ok', '상담 신청이 접수됐어요! 가까운 지점에서 곧 연락드릴게요. 😊');
    } catch {
      showMsg('err', '전송에 실패했어요. 잠시 후 다시 시도하거나 010-8241-2051로 전화 주세요.');
    } finally {
      btn.disabled = false;
    }
  });
}

// 신청서가 화면에 보이면 떠 있는 버튼 숨기기
const floatCta = document.getElementById('floatCta');
const apply = document.getElementById('apply');
if (floatCta && apply) {
  new IntersectionObserver(([en]) => {
    floatCta.style.display = en.isIntersecting ? 'none' : '';
  }).observe(apply);
}
