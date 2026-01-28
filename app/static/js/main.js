/**
 * Local Crust - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {
    // Initialize components
    initFlashMessages();
    initNavigation();
    initForms();
});

/**
 * Flash Messages - Auto dismiss
 */
function initFlashMessages() {
    const alerts = document.querySelectorAll('.alert');

    alerts.forEach(alert => {
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            alert.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => alert.remove(), 300);
        }, 5000);

        // Close button
        const closeBtn = alert.querySelector('.alert-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                alert.style.animation = 'slideOut 0.3s ease forwards';
                setTimeout(() => alert.remove(), 300);
            });
        }
    });
}

// Add slideOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from { opacity: 1; transform: translateX(0); }
        to { opacity: 0; transform: translateX(100%); }
    }
`;
document.head.appendChild(style);

/**
 * Navigation - Mobile toggle
 */
function initNavigation() {
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.querySelector('.nav-links');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }
}

/**
 * Form enhancements
 */
function initForms() {
    // Character counters for textareas
    const textareas = document.querySelectorAll('textarea[maxlength]');
    textareas.forEach(textarea => {
        const maxLength = textarea.getAttribute('maxlength');
        const counter = document.createElement('span');
        counter.className = 'char-counter';
        counter.textContent = `0/${maxLength}`;
        textarea.parentNode.appendChild(counter);

        textarea.addEventListener('input', () => {
            counter.textContent = `${textarea.value.length}/${maxLength}`;
        });
    });
}

/**
 * Add to Cart - AJAX
 */
async function addToCart(productId, quantity = 1) {
    try {
        const response = await fetch('/api/cart/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                product_id: productId,
                quantity: quantity
            })
        });

        const data = await response.json();

        if (data.success) {
            updateCartBadge(data.cart_count);
            showToast(data.message, 'success');
        } else {
            showToast(data.message, 'danger');
        }

        return data;
    } catch (error) {
        console.error('Error adding to cart:', error);
        showToast('Error adding to cart', 'danger');
    }
}

/**
 * Update cart badge
 */
function updateCartBadge(count) {
    const badge = document.querySelector('.cart-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'flex' : 'none';
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const container = document.querySelector('.flash-container') || createFlashContainer();

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;

    const iconMap = {
        success: 'check-circle',
        danger: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };

    alert.innerHTML = `
        <i class="fas fa-${iconMap[type]}"></i>
        <span>${message}</span>
        <button class="alert-close">&times;</button>
    `;

    container.appendChild(alert);

    // Auto dismiss
    setTimeout(() => {
        alert.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => alert.remove(), 300);
    }, 5000);

    // Close button
    alert.querySelector('.alert-close').addEventListener('click', () => {
        alert.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => alert.remove(), 300);
    });
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-container';
    document.body.appendChild(container);
    return container;
}

/**
 * Get CSRF Token
 */
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');

    const input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;

    return '';
}

/**
 * Quantity controls
 */
function updateQuantity(btn, delta) {
    const form = btn.closest('.quantity-form');
    const input = form.querySelector('.qty-input');
    let value = parseInt(input.value) + delta;
    if (value < 1) value = 1;
    if (value > 99) value = 99;
    input.value = value;
    form.submit();
}

/**
 * Toggle password visibility
 */
function togglePassword(btn) {
    const input = btn.previousElementSibling;
    const icon = btn.querySelector('i');

    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

/**
 * Search autocomplete (basic)
 */
let searchTimeout;
function initSearchAutocomplete() {
    const searchInput = document.querySelector('.nav-search input');

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);

            const query = e.target.value.trim();
            if (query.length < 2) return;

            searchTimeout = setTimeout(async () => {
                try {
                    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                    const data = await response.json();
                    // Handle autocomplete results
                    console.log('Search results:', data);
                } catch (error) {
                    console.error('Search error:', error);
                }
            }, 300);
        });
    }
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 0
    }).format(amount);
}
