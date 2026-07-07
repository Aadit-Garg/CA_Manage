/**
 * CA Manage — Application JavaScript
 * 
 * Service Worker registration, toast system, HTMX config,
 * and mobile UX enhancements.
 */

// ═══════════════════════════════════════════════════════════════════
// Service Worker Registration
// ═══════════════════════════════════════════════════════════════════
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker
            .register('/sw.js', { scope: '/' })
            .then((registration) => {
                console.log('[CA Manage] Service Worker registered:', registration.scope);

                // Check for updates periodically
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'activated') {
                            showToast('App updated! Refresh for the latest version.', 'info');
                        }
                    });
                });
            })
            .catch((err) => {
                console.warn('[CA Manage] Service Worker registration failed:', err);
            });
    });
}


// ═══════════════════════════════════════════════════════════════════
// Toast Notification System
// ═══════════════════════════════════════════════════════════════════
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const iconMap = {
        success: 'bi-check-circle-fill text-success',
        danger: 'bi-exclamation-triangle-fill text-danger',
        error: 'bi-exclamation-triangle-fill text-danger',
        warning: 'bi-exclamation-circle-fill text-warning',
        info: 'bi-info-circle-fill text-info',
    };

    const iconClass = iconMap[type] || iconMap.info;

    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center border-0 ca-toast';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body d-flex align-items-center gap-2">
                <i class="bi ${iconClass} fs-5"></i>
                <span>${message}</span>
            </div>
            <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    container.appendChild(toastEl);

    const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 5000 });
    toast.show();

    // Clean up after hidden
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });
}


// ═══════════════════════════════════════════════════════════════════
// Auto-initialize Bootstrap toasts on page load
// ═══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    // Initialize any server-rendered toasts
    document.querySelectorAll('.toast.show').forEach((toastEl) => {
        const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 5000 });
        toast.show();
    });

    // Close offcanvas sidebar on nav link click (mobile)
    const sidebar = document.getElementById('sidebarOffcanvas');
    if (sidebar) {
        const offcanvasInstance = bootstrap.Offcanvas.getOrCreateInstance(sidebar);
        sidebar.querySelectorAll('.ca-nav-link').forEach((link) => {
            link.addEventListener('click', () => {
                // Only close on mobile
                if (window.innerWidth < 992) {
                    offcanvasInstance.hide();
                }
            });
        });
    }
});


// ═══════════════════════════════════════════════════════════════════
// HTMX Configuration
// ═══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    if (typeof htmx !== 'undefined') {
        // Global HTMX error handling
        document.body.addEventListener('htmx:responseError', (event) => {
            const status = event.detail.xhr?.status;
            if (status === 403) {
                showToast('Access denied. You don\'t have permission.', 'danger');
            } else if (status === 429) {
                showToast('Too many requests. Please slow down.', 'warning');
            } else if (status >= 500) {
                showToast('Server error. Please try again.', 'danger');
            }
        });

        // Show loading indicators
        document.body.addEventListener('htmx:beforeRequest', () => {
            // Optional: add global loading state
        });

        document.body.addEventListener('htmx:afterRequest', () => {
            // Optional: remove global loading state
        });
    }
});


// ═══════════════════════════════════════════════════════════════════
// Mobile viewport height fix (100vh issue on mobile browsers)
// ═══════════════════════════════════════════════════════════════════
function setViewportHeight() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
}

setViewportHeight();
window.addEventListener('resize', setViewportHeight);


// ═══════════════════════════════════════════════════════════════════
// Bottom nav active state
// ═══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.ca-bottom-nav-item').forEach((item) => {
        const href = item.getAttribute('href');
        if (href && href !== '#' && currentPath.startsWith(href)) {
            item.classList.add('active');
        }
    });
});
