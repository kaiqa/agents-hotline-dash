const loginForm = document.getElementById('login-form');
const errorMessage = document.getElementById('form-error');
const submitButton = document.getElementById('submit-button');
const passwordInput = document.getElementById('password');
const passwordToggle = document.getElementById('password-toggle');

passwordToggle.addEventListener('click', () => {
    const showPassword = passwordInput.type === 'password';
    passwordInput.type = showPassword ? 'text' : 'password';
    passwordToggle.setAttribute('aria-label', showPassword ? 'Hide password' : 'Show password');
});

loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorMessage.textContent = '';
    submitButton.disabled = true;
    submitButton.querySelector('span').textContent = 'Signing in...';

    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: loginForm.elements.username.value,
                password: loginForm.elements.password.value,
            }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Unable to sign in.');
        window.location.assign('/');
    } catch (error) {
        errorMessage.textContent = error.message === 'Login credentials are not configured'
            ? 'Login is not configured. Set LOGIN_USERNAME, LOGIN_PASSWORD, and SESSION_SECRET in .env.'
            : error.message;
    } finally {
        submitButton.disabled = false;
        submitButton.querySelector('span').textContent = 'Sign in to dashboard';
    }
});
