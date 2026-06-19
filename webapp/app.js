const tg = window.Telegram?.WebApp;
const API = window.location.origin;

let profile = null;
let cart = { items: [], total: 0 };
let searchTimeout = null;

const STATUS_LABELS = {
  new: 'Новый',
  processing: 'В обработке',
  shipped: 'Отправлен',
  delivered: 'Доставлен',
  cancelled: 'Отменён',
};

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor('#8b4513');
    tg.setBackgroundColor('#faf7f2');
  }

  document.getElementById('searchInput').addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadProducts(), 300);
  });

  showLoader(true);
  try {
    await Promise.all([
      loadProfile(),
      loadCountries(),
      loadProducts(),
      loadCart(),
    ]);
  } catch (err) {
    console.error('Init error:', err);
  }
  showLoader(false);
});

// ── API helpers ──────────────────────────────────────────────────────────────

function getHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (tg?.initData) {
    headers['X-Telegram-Init-Data'] = tg.initData;
  }
  return headers;
}

async function api(method, path, body) {
  const opts = { method, headers: getHeaders() };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function showLoader(show) {
  document.getElementById('loader').classList.toggle('hidden', !show);
}

function formatPrice(price) {
  return `${Math.round(price).toLocaleString('ru-RU')} ₽`;
}

// ── Navigation ─────────────────────────────────────────────────────────────────

function showPage(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));

  const pageEl = document.getElementById(`page-${page}`);
  if (pageEl) pageEl.classList.add('active');

  const tab = document.querySelector(`.nav-tab[data-page="${page}"]`);
  if (tab) tab.classList.add('active');

  if (page === 'cart') renderCart();
  if (page === 'profile') loadProfileData();
  if (page === 'checkout') prepareCheckout();
}

function switchProfileTab(tab) {
  document.querySelectorAll('.profile-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.profile-tab-content').forEach(t => t.classList.remove('active'));
  document.querySelector(`.profile-tab[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');

  if (tab === 'orders') loadOrders();
  if (tab === 'favorites') loadFavorites();
  if (tab === 'promotions') loadPromotions();
}

// ── Profile ────────────────────────────────────────────────────────────────────

async function loadProfile() {
  profile = await api('GET', '/api/profile');
  document.getElementById('profileName').textContent = profile.first_name || 'Гость';
  document.getElementById('profileCity').textContent = profile.city ? `📍 ${profile.city}` : 'Город не указан';

  if (tg?.initDataUnsafe?.user?.photo_url) {
    document.getElementById('profileAvatar').innerHTML =
      `<img src="${tg.initDataUnsafe.user.photo_url}" alt="avatar">`;
  }
}

function loadProfileData() {
  loadProfile();
  loadOrders();
}

// ── Catalog ────────────────────────────────────────────────────────────────────

async function loadCountries() {
  const countries = await api('GET', '/api/countries');
  const select = document.getElementById('countryFilter');
  countries.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    select.appendChild(opt);
  });
  select.addEventListener('change', loadCategories);
  await loadCategories();
}

async function loadCategories() {
  const country = document.getElementById('countryFilter').value;
  const categories = await api('GET', `/api/categories${country ? '?country=' + encodeURIComponent(country) : ''}`);
  const select = document.getElementById('categoryFilter');
  select.innerHTML = '<option value="">Все категории</option>';
  categories.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    select.appendChild(opt);
  });
}

async function loadProducts() {
  const country = document.getElementById('countryFilter').value;
  const category = document.getElementById('categoryFilter').value;
  const search = document.getElementById('searchInput').value.trim();

  let url = '/api/products?';
  if (country) url += `country=${encodeURIComponent(country)}&`;
  if (category) url += `category=${encodeURIComponent(category)}&`;
  if (search) url += `search=${encodeURIComponent(search)}&`;

  const products = await api('GET', url);
  renderProducts(products);
}

function renderProducts(products) {
  const list = document.getElementById('productsList');
  const empty = document.getElementById('catalogEmpty');

  if (!products.length) {
    list.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  list.innerHTML = products.map(p => `
    <div class="product-card" onclick="openProduct(${p.id})">
      <div class="product-card-body">
        <div class="product-country">${p.country} · ${p.category}</div>
        <div class="product-name">${escHtml(p.name)}</div>
        <div class="product-price">${formatPrice(p.price)}</div>
        <div class="product-actions" onclick="event.stopPropagation()">
          <button class="btn btn-primary" onclick="addToCart(${p.id})">В корзину</button>
          <button class="btn btn-fav ${p.is_favorite ? 'active' : ''}" onclick="toggleFavorite(${p.id}, this)">❤️</button>
        </div>
      </div>
    </div>
  `).join('');
}

async function openProduct(id) {
  showLoader(true);
  try {
    const p = await api('GET', `/api/products/${id}`);
    document.getElementById('productDetail').innerHTML = `
      <div class="detail-country">${p.country} · ${p.category}</div>
      <div class="detail-name">${escHtml(p.name)}</div>
      <div class="detail-price">${formatPrice(p.price)}</div>
      <div class="detail-desc">${escHtml(p.description || '')}</div>
      <div class="detail-actions">
        <button class="btn btn-primary" onclick="addToCart(${p.id}); closeProductModal()">В корзину</button>
        <button class="btn btn-fav ${p.is_favorite ? 'active' : ''}" onclick="toggleFavorite(${p.id}, this)">❤️</button>
      </div>
    `;
    document.getElementById('productModal').classList.remove('hidden');
  } finally {
    showLoader(false);
  }
}

function closeProductModal() {
  document.getElementById('productModal').classList.add('hidden');
}

// ── Favorites ──────────────────────────────────────────────────────────────────

async function toggleFavorite(productId, btn) {
  const result = await api('POST', '/api/favorites/toggle', { product_id: productId });
  if (btn) {
    btn.classList.toggle('active', result.is_favorite);
  }
  if (tg) tg.HapticFeedback?.impactOccurred('light');
}

async function loadFavorites() {
  const favorites = await api('GET', '/api/favorites');
  const list = document.getElementById('favoritesList');
  const empty = document.getElementById('favoritesEmpty');

  if (!favorites.length) {
    list.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  renderProductsIn(list, favorites);
}

function renderProductsIn(container, products) {
  container.innerHTML = products.map(p => `
    <div class="product-card" onclick="openProduct(${p.id})">
      <div class="product-card-body">
        <div class="product-country">${p.country}</div>
        <div class="product-name">${escHtml(p.name)}</div>
        <div class="product-price">${formatPrice(p.price)}</div>
        <div class="product-actions" onclick="event.stopPropagation()">
          <button class="btn btn-primary" onclick="addToCart(${p.id})">В корзину</button>
          <button class="btn btn-fav active" onclick="toggleFavorite(${p.id}, this); loadFavorites()">❤️</button>
        </div>
      </div>
    </div>
  `).join('');
}

// ── Cart ───────────────────────────────────────────────────────────────────────

async function loadCart() {
  cart = await api('GET', '/api/cart');
  updateCartBadge();
}

function updateCartBadge() {
  const count = cart.items.reduce((s, i) => s + i.quantity, 0);
  document.getElementById('cartCount').textContent = count;
}

async function addToCart(productId) {
  const existing = cart.items.find(i => i.id === productId);
  const qty = existing ? existing.quantity + 1 : 1;
  cart = await api('POST', '/api/cart/update', { product_id: productId, quantity: qty });
  updateCartBadge();
  if (tg) {
    tg.HapticFeedback?.notificationOccurred('success');
    tg.showAlert?.('Товар добавлен в корзину');
  }
}

async function updateCartQty(productId, delta) {
  const existing = cart.items.find(i => i.id === productId);
  if (!existing) return;
  const qty = existing.quantity + delta;
  cart = await api('POST', '/api/cart/update', { product_id: productId, quantity: qty });
  updateCartBadge();
  renderCart();
}

function renderCart() {
  const list = document.getElementById('cartItems');
  const empty = document.getElementById('cartEmpty');
  const footer = document.getElementById('cartFooter');

  if (!cart.items.length) {
    list.innerHTML = '';
    empty.classList.remove('hidden');
    footer.classList.add('hidden');
    return;
  }
  empty.classList.add('hidden');
  footer.classList.remove('hidden');

  list.innerHTML = cart.items.map(i => `
    <div class="cart-item">
      <div class="cart-item-info">
        <div class="cart-item-name">${escHtml(i.name)}</div>
        <div class="cart-item-price">${formatPrice(i.price * i.quantity)}</div>
      </div>
      <div class="qty-control">
        <button class="qty-btn" onclick="updateCartQty(${i.id}, -1)">−</button>
        <span class="qty-value">${i.quantity}</span>
        <button class="qty-btn" onclick="updateCartQty(${i.id}, 1)">+</button>
      </div>
    </div>
  `).join('');

  document.getElementById('cartTotal').textContent = formatPrice(cart.total);
}

// ── Checkout ───────────────────────────────────────────────────────────────────

function showCheckout() {
  if (!cart.items.length) return;
  showPage('checkout');
}

function prepareCheckout() {
  document.getElementById('orderName').value = profile?.first_name || '';
}

async function submitOrder(e) {
  e.preventDefault();
  showLoader(true);
  try {
    const result = await api('POST', '/api/orders', {
      phone: document.getElementById('orderPhone').value.trim(),
      address: document.getElementById('orderAddress').value.trim(),
      comment: document.getElementById('orderComment').value.trim(),
    });

    document.getElementById('successOrderId').textContent =
      `Заказ №${result.order_id} на сумму ${formatPrice(result.total)}`;
    document.getElementById('paymentDetails').textContent = result.payment_details;

    cart = { items: [], total: 0 };
    updateCartBadge();

    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-success').classList.add('active');

    if (tg) tg.sendData(JSON.stringify({ type: 'order', order_id: result.order_id, total: result.total }));
  } catch (err) {
    if (tg) tg.showAlert(err.message);
    else alert(err.message);
  } finally {
    showLoader(false);
  }
}

// ── Orders ─────────────────────────────────────────────────────────────────────

async function loadOrders() {
  const orders = await api('GET', '/api/orders');
  const list = document.getElementById('ordersList');
  const empty = document.getElementById('ordersEmpty');

  if (!orders.length) {
    list.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  list.innerHTML = orders.map(o => {
    const items = o.items.map(i => `${i.product_name} × ${i.quantity}`).join(', ');
    return `
      <div class="order-card">
        <div class="order-card-header">
          <strong>Заказ #${o.id}</strong>
          <span class="order-status ${o.status}">${STATUS_LABELS[o.status] || o.status}</span>
        </div>
        <div style="font-size:0.85rem;color:var(--text-muted)">${items}</div>
        <div style="margin-top:6px;font-weight:700;color:var(--primary)">${formatPrice(o.total)}</div>
        <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">${o.created_at?.slice(0, 10)}</div>
      </div>
    `;
  }).join('');
}

// ── Promotions ─────────────────────────────────────────────────────────────────

async function loadPromotions() {
  const data = await api('GET', '/api/promotions');
  document.getElementById('promotionsList').innerHTML = data.promotions.map(p => `
    <div class="promo-card${p.link ? ' promo-clickable' : ''}" ${p.link ? `onclick="window.open('${p.link}', '_blank')"` : ''}>
      <h3>${escHtml(p.title)}</h3>
      <p>${escHtml(p.description)}</p>
    </div>
  `).join('');
  const channelBtn = document.getElementById('channelLink');
  if (data.channel_url) {
    channelBtn.href = data.channel_url;
    channelBtn.textContent = `📢 Подписаться на ${data.channel}`;
    channelBtn.classList.remove('hidden');
  }
}

// ── Utils ──────────────────────────────────────────────────────────────────────

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
