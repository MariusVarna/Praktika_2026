// Footer Navigation Handler
document.addEventListener('DOMContentLoaded', () => {
  const footerBtns = {
    login: document.getElementById('loginBtn'),
    help: document.getElementById('helpBtn'),
    feedback: document.getElementById('feedbackBtn'),
    settings: document.getElementById('settingsBtn'),
    back: document.getElementById('backBtn'),
    home: document.getElementById('homeBtn'),
  };

  // Navigation mapping
  const navMap = {
    login: '/pages/join.html',
    help: '/pages/help.html',
    feedback: () => alert('Thank you for your feedback! We appreciate your input.'),
    settings: '/pages/settings.html',
    home: '/pages/join.html',
    back: () => window.history.back(),
  };

  // Attach click handlers
  Object.keys(footerBtns).forEach(key => {
    const btn = footerBtns[key];
    if (btn) {
      btn.addEventListener('click', () => {
        const action = navMap[key];
        if (typeof action === 'function') {
          action();
        } else if (action) {
          window.location.href = action;
        }
      });
    }
  });
});
