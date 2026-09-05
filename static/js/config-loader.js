/**
 * Exhibition Guru - Config Loader
 * Fetches config.json from backend API (/api/config) and updates social links,
 * contact info, map URL, and company info dynamically.
 */

document.addEventListener('DOMContentLoaded', () => {
  fetchConfig();
});

async function fetchConfig() {
  try {
    const response = await fetch('/api/config');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const config = await response.json();
    applyConfig(config);
  } catch (error) {
    console.warn('Could not load dynamic config from API, using fallback embedded data:', error);
  }
}

function applyConfig(config) {
  if (!config) return;

  // 1. Update Social Media Links
  const social = config.social_media || {};
  
  // Facebook
  document.querySelectorAll('.social-facebook').forEach(el => {
    if (social.facebook) el.href = social.facebook;
  });

  // Instagram
  document.querySelectorAll('.social-instagram').forEach(el => {
    if (social.instagram) el.href = social.instagram;
  });

  // LinkedIn
  document.querySelectorAll('.social-linkedin').forEach(el => {
    if (social.linkedin) el.href = social.linkedin;
  });

  // YouTube
  document.querySelectorAll('.social-youtube').forEach(el => {
    if (social.youtube) el.href = social.youtube;
  });

  // Twitter / X
  document.querySelectorAll('.social-twitter').forEach(el => {
    if (social.x_twitter) el.href = social.x_twitter;
  });

  // WhatsApp Floating Button & Links
  const whatsappUrl = social.whatsapp || "https://wa.me/919876543210";
  document.querySelectorAll('.whatsapp-link').forEach(el => {
    el.href = whatsappUrl;
  });

  // 2. Update Contact Details
  const contact = config.contact_info || {};
  if (contact.phone) {
    document.querySelectorAll('.phone-text').forEach(el => el.textContent = contact.phone);
    document.querySelectorAll('.phone-link').forEach(el => el.href = `tel:${contact.phone.replace(/\s+/g, '')}`);
  }
  if (contact.email) {
    document.querySelectorAll('.email-text').forEach(el => el.textContent = contact.email);
    document.querySelectorAll('.email-link').forEach(el => el.href = `mailto:${contact.email}`);
  }
  if (contact.address) {
    document.querySelectorAll('.address-text').forEach(el => el.textContent = contact.address);
  }

  // 3. Update Google Map Links
  const mapData = config.google_map || {};
  if (mapData.direct_url) {
    document.querySelectorAll('.google-map-btn').forEach(el => {
      el.href = mapData.direct_url;
    });
  }
  if (mapData.embed_url) {
    const mapIframe = document.querySelector('#google-map-iframe');
    if (mapIframe) {
      mapIframe.src = mapData.embed_url;
    }
  }

  console.log('✅ Exhibition Guru config applied successfully.');
}
