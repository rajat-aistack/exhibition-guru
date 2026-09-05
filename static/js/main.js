/**
 * Exhibition Guru - Main Interaction Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initPortfolioFilter();
  initLightbox();
  initFaqAccordion();
  initQuoteForm();
});

/* 1. Navbar & Mobile Menu */
function initNavbar() {
  const navbar = document.querySelector('.navbar');
  const menuToggle = document.querySelector('.menu-toggle');
  const navLinks = document.querySelector('.nav-links');

  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.style.background = 'rgba(11, 11, 14, 0.95)';
      navbar.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.7)';
    } else {
      navbar.style.background = 'rgba(11, 11, 14, 0.85)';
      navbar.style.boxShadow = 'none';
    }
  });

  if (menuToggle) {
    menuToggle.addEventListener('click', () => {
      navLinks.classList.toggle('active');
    });
  }
}

/* 2. Portfolio Filter */
function initPortfolioFilter() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  const portfolioItems = document.querySelectorAll('.portfolio-item');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filterValue = btn.getAttribute('data-filter');

      portfolioItems.forEach(item => {
        const category = item.getAttribute('data-category');
        if (filterValue === 'all' || category === filterValue) {
          item.style.display = 'block';
          setTimeout(() => {
            item.style.opacity = '1';
            item.style.transform = 'scale(1)';
          }, 50);
        } else {
          item.style.opacity = '0';
          item.style.transform = 'scale(0.9)';
          setTimeout(() => {
            item.style.display = 'none';
          }, 300);
        }
      });
    });
  });
}

/* 3. Lightbox Modal */
function initLightbox() {
  const modal = document.querySelector('#lightbox-modal');
  const modalImg = document.querySelector('#modal-img');
  const modalTitle = document.querySelector('#modal-title');
  const modalCategory = document.querySelector('#modal-category');
  const modalSpecs = document.querySelector('#modal-specs');
  const closeBtn = document.querySelector('.modal-close');

  if (!modal) return;

  document.querySelectorAll('.view-project-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const card = btn.closest('.portfolio-item');
      const imgSrc = card.querySelector('.portfolio-img img').src;
      const title = card.querySelector('h3').textContent;
      const category = card.querySelector('.badge-gold').textContent;
      const specs = card.querySelector('p').textContent;

      modalImg.src = imgSrc;
      modalTitle.textContent = title;
      modalCategory.textContent = category;
      modalSpecs.textContent = specs;

      modal.classList.add('active');
    });
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modal.classList.remove('active');
    });
  }

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.remove('active');
    }
  });
}

/* 4. FAQ Accordion Interaction */
function initFaqAccordion() {
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const header = item.querySelector('.faq-header');
    if (!header) return;

    header.addEventListener('click', (e) => {
      e.preventDefault();
      const isActive = item.classList.contains('active');

      // Close all items
      faqItems.forEach(i => i.classList.remove('active'));

      // Toggle current item
      if (!isActive) {
        item.classList.add('active');
      }
    });
  });
}

/* 5. Quote Form Submit Handler */
function initQuoteForm() {
  const quoteForm = document.querySelector('#quote-form');
  const responseBox = document.querySelector('#form-response');

  if (!quoteForm) return;

  quoteForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(quoteForm);
    const data = Object.fromEntries(formData.entries());

    const submitBtn = quoteForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '⏳ Submitting Inquiries...';
    submitBtn.disabled = true;

    try {
      const response = await fetch('/api/quote', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (responseBox) {
        responseBox.style.display = 'block';
        responseBox.className = 'alert alert-success';
        responseBox.innerHTML = `✨ <strong>Success!</strong> ${result.message}`;
      }

      quoteForm.reset();
    } catch (error) {
      if (responseBox) {
        responseBox.style.display = 'block';
        responseBox.className = 'alert alert-danger';
        responseBox.innerHTML = `⚠️ Error sending inquiry. Please call us directly or click WhatsApp.`;
      }
    } finally {
      submitBtn.innerHTML = originalText;
      submitBtn.disabled = false;
    }
  });
}
