/* ============================================================
   ZAID INDUSTRIES — main.js
   ============================================================ */

// ---- NAV SCROLL STATE ----
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('nav--scrolled', window.scrollY > 20);
}, { passive: true });

// ---- MOBILE NAV TOGGLE ----
const navToggle = document.getElementById('navToggle');
const navLinks  = document.getElementById('navLinks');

navToggle.addEventListener('click', () => {
  const open = navLinks.classList.toggle('open');
  navToggle.setAttribute('aria-expanded', String(open));
});

// Close mobile nav when a link is clicked
navLinks.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    navLinks.classList.remove('open');
    navToggle.setAttribute('aria-expanded', 'false');
  });
});

// ---- COUNTER ANIMATION ----
function animateCounter(el, target, suffix) {
  const duration = 1800;
  const start    = performance.now();
  const step = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const value    = Math.round(eased * target);
    el.textContent = value;
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ---- TERMINAL AUTOMATION COUNTER ----
function animateTerminalCount(el, target) {
  const duration = 2400;
  const start    = performance.now();
  const step = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(eased * target).toString().padStart(4, '0');
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ---- INTERSECTION OBSERVER ----
const observerOptions = {
  threshold: 0.2,
  rootMargin: '0px 0px -60px 0px',
};

// Counter observer
const counterObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    counterObserver.unobserve(entry.target);
    const target = parseInt(entry.target.dataset.target, 10);
    animateCounter(entry.target, target);
  });
}, observerOptions);

document.querySelectorAll('[data-target]').forEach(el => {
  counterObserver.observe(el);
});

// Terminal count observer
const automationEl = document.getElementById('automationCount');
if (automationEl) {
  const terminalObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      terminalObserver.unobserve(entry.target);
      animateTerminalCount(entry.target, 2847);
    });
  }, observerOptions);
  terminalObserver.observe(automationEl);
}

// Fade-in observer for cards and sections
const fadeObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      fadeObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll(
  '.system-card, .product-card, .spec-group, .trait, .about__left, .about__right'
).forEach(el => {
  el.classList.add('fade-in');
  fadeObserver.observe(el);
});

// Inject fade-in CSS
const fadeStyle = document.createElement('style');
fadeStyle.textContent = `
  .fade-in {
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.5s ease, transform 0.5s ease;
  }
  .fade-in.visible {
    opacity: 1;
    transform: translateY(0);
  }
`;
document.head.appendChild(fadeStyle);

// ---- CONTACT FORM ----
const form       = document.getElementById('contactForm');
const successMsg = document.getElementById('formSuccess');

if (form) {
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.querySelector('span').textContent = 'Sending...';

    // Simulate async submission
    setTimeout(() => {
      form.style.display = 'none';
      successMsg.classList.add('visible');
    }, 1000);
  });
}

// ---- SMOOTH ACTIVE NAV HIGHLIGHT ----
const sections  = document.querySelectorAll('section[id]');
const navAnchors = document.querySelectorAll('.nav__links a[href^="#"]');

const sectionObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const id = entry.target.getAttribute('id');
    navAnchors.forEach(a => {
      a.classList.toggle('active', a.getAttribute('href') === `#${id}`);
    });
  });
}, { threshold: 0.4 });

sections.forEach(s => sectionObserver.observe(s));

// Inject active nav link style
const navActiveStyle = document.createElement('style');
navActiveStyle.textContent = `
  .nav__links a.active:not(.nav__cta) {
    color: var(--metal);
  }
`;
document.head.appendChild(navActiveStyle);
