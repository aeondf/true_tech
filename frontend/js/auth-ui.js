// Authentication screen logic.

let authEmailVal = '';
let regMode = false;

function toggleRegMode() {
  regMode = !regMode;
  document.getElementById('authConfirmWrap').style.display = regMode ? 'block' : 'none';
  document.getElementById('authConfirmPwd').value = '';
  document.getElementById('authCodeBtn').textContent = regMode ? 'Create account' : 'Sign in';
  document.getElementById('authStep2Title').textContent = regMode ? 'Create account' : 'Enter password';
  document.getElementById('authModeToggleText').textContent = regMode
    ? 'Already have an account? Sign in ->'
    : 'No account yet? Register ->';
}

function authSubmitEmail() {
  const input = document.getElementById('authEmail');
  const value = input.value.trim();
  if (!value || !value.includes('@')) {
    input.style.borderColor = 'var(--red)';
    input.focus();
    setTimeout(() => { input.style.borderColor = ''; }, 1200);
    return;
  }

  authEmailVal = value;
  document.getElementById('authEmailShow').textContent = value;
  const step1 = document.getElementById('authStep1');
  step1.classList.add('exit-left');
  setTimeout(() => {
    step1.style.display = 'none';
    step1.classList.remove('exit-left');
    const step2 = document.getElementById('authStep2');
    step2.style.display = 'flex';
    step2.style.opacity = '1';
    step2.classList.add('enter-right');
    setTimeout(() => step2.classList.remove('enter-right'), 450);
    setTimeout(() => document.getElementById('authPassword')?.focus(), 80);
  }, 290);
}

function authGoBack() {
  const step2 = document.getElementById('authStep2');
  step2.classList.add('exit-left');
  setTimeout(() => {
    step2.style.display = 'none';
    step2.classList.remove('exit-left');
    document.getElementById('authPassword').value = '';
    document.getElementById('authConfirmPwd').value = '';

    if (regMode) {
      regMode = false;
      document.getElementById('authConfirmWrap').style.display = 'none';
      document.getElementById('authCodeBtn').textContent = 'Sign in';
      document.getElementById('authStep2Title').textContent = 'Enter password';
      document.getElementById('authModeToggleText').textContent = 'No account yet? Register ->';
    }

    const step1 = document.getElementById('authStep1');
    step1.style.display = 'flex';
    step1.classList.add('enter-right');
    setTimeout(() => step1.classList.remove('enter-right'), 450);
    setTimeout(() => document.getElementById('authEmail')?.focus(), 80);
  }, 290);
}

function togglePwdVis() {
  const input = document.getElementById('authPassword');
  const icon = document.getElementById('pwdEyeIcon');
  if (input.type === 'password') {
    input.type = 'text';
    icon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/>';
  } else {
    input.type = 'password';
    icon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
  }
}

function _authSuccess(data) {
  authToken = data.token;
  currentUserId = data.user_id;
  localStorage.setItem('mts-token', authToken);
  localStorage.setItem('mts-user-id', currentUserId);
  localStorage.setItem('mts-user-email', data.email);
  document.getElementById('profInpEmail').value = data.email;

  const savedName = localStorage.getItem('mts-display-name');
  const displayName = savedName || data.email.split('@')[0];
  document.getElementById('profInpName').value = displayName;
  document.getElementById('sbUserName').textContent = displayName;
  document.getElementById('sbAvatar').textContent = getInitials(displayName);

  const org = localStorage.getItem('mts-org') || '';
  if (org) document.getElementById('profInpOrg').value = org;

  document.getElementById('authScreen').classList.add('out');
  setTimeout(() => {
    document.getElementById('authScreen').style.display = 'none';
    initSplash();
  }, 680);
}

function authSubmitCode() {
  const password = document.getElementById('authPassword').value;
  if (!password) {
    const input = document.getElementById('authPassword');
    input.style.borderColor = 'var(--red)';
    input.focus();
    setTimeout(() => { input.style.borderColor = ''; }, 1200);
    return;
  }

  const button = document.getElementById('authCodeBtn');

  if (regMode) {
    if (password.length < 6) {
      toast('Password must contain at least 6 characters', 'err');
      return;
    }

    const confirmPassword = document.getElementById('authConfirmPwd').value;
    if (!confirmPassword) {
      const input = document.getElementById('authConfirmPwd');
      input.style.borderColor = 'var(--red)';
      input.focus();
      setTimeout(() => { input.style.borderColor = ''; }, 1200);
      return;
    }
    if (password !== confirmPassword) {
      toast('Passwords do not match', 'err');
      return;
    }

    button.textContent = 'Creating...';
    button.disabled = true;
    apiAuthRegister(authEmailVal, password)
      .then(_authSuccess)
      .catch(error => {
        button.textContent = 'Create account';
        button.disabled = false;
        toast(error.message || 'Registration failed', 'err', 3000);
      });
  } else {
    button.textContent = 'Signing in...';
    button.disabled = true;
    apiAuthLogin(authEmailVal, password)
      .then(_authSuccess)
      .catch(error => {
        button.textContent = 'Sign in';
        button.disabled = false;
        const input = document.getElementById('authPassword');
        input.style.borderColor = 'var(--red)';
        input.focus();
        setTimeout(() => { input.style.borderColor = ''; }, 1800);
        toast(error.message || 'Wrong password', 'err', 3000);
      });
  }
}

function initSplash() {
  const letters = ['sl-m', 'sl-t', 'sl-s'];
  setTimeout(() => {
    const brain = document.getElementById('splash-brain');
    brain?.classList.add('show');
    setTimeout(() => brain?.classList.add('glow'), 700);
  }, 200);
  letters.forEach((id, index) => {
    setTimeout(() => document.getElementById(id)?.classList.add('lit'), 500 + index * 200);
  });
  setTimeout(burstParticles, 1200);
  setTimeout(() => document.getElementById('splash-sub')?.classList.add('show'), 1550);
  setTimeout(() => document.getElementById('splash-letters')?.classList.add('gather'), 2100);
  setTimeout(() => {
    document.getElementById('splash')?.classList.add('out');
    document.getElementById('appRoot')?.classList.add('vis');
  }, 2900);
  setTimeout(() => {
    document.getElementById('splash')?.remove();
    fetchModels();
    loadHistory();
    loadMemory();
    checkHealth();
    currentConvId = uuid();
  }, 3600);
}

async function checkHealth() {
  try {
    const response = await fetch(`${API}/health`, { signal: AbortSignal.timeout(4000) });
    const data = await response.json();
    toast(data.status === 'ok' ? 'Backend connected' : 'Backend is in degraded mode', data.status === 'ok' ? 'ok' : 'inf', 2500);
  } catch {
    toast('Backend is unavailable', 'err', 5000);
  }
}
