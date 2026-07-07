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

// ═══════════════════════════════════════════════════════════════════
// Force PWA push notification prompt on page load
// ═══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', async () => {
    // Wait 2 seconds, then check if we should prompt the user
    setTimeout(async () => {
        const enableBtn = document.getElementById('enableWebPushBtn');
        if (!enableBtn) return; // Not logged in or button not present

        // If the button is already marked as Enabled, don't show the prompt
        if (enableBtn.innerHTML.includes('Enabled')) return;

        if ('serviceWorker' in navigator && 'PushManager' in window) {
            const permission = Notification.permission;
            if (permission === 'default') {
                showPushPromptModal();
            }
        }
    }, 2500);
});

function showPushPromptModal() {
    if (document.getElementById('pushPromptModal')) return;

    const modalHTML = 
    <div class="modal fade" id="pushPromptModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
        <div class="modal-dialog modal-dialog-centered" style="max-width: 360px; margin: 1.75rem auto;">
            <div class="modal-content" style="border-radius: 16px; border: none; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.15);">
                <div class="modal-body text-center p-4">
                    <div class="rounded-circle bg-primary bg-opacity-10 text-primary d-inline-flex align-items-center justify-content-center mb-3" style="width: 64px; height: 64px;">
                        <i class="bi bi-bell-fill fs-3 animate-bell"></i>
                    </div>
                    <h5 class="fw-bold mb-2">Stay Updated</h5>
                    <p class="text-muted small px-2">Enable OS and push notifications to receive real-time alerts for document approvals, uploads, and firm messages.</p>
                    <div class="d-flex flex-column gap-2 mt-4">
                        <button class="btn btn-primary w-100 py-2 fw-medium btn-sm" onclick="enablePushFromModal()">
                            Enable Notifications
                        </button>
                        <button class="btn btn-link text-muted btn-sm text-decoration-none" data-bs-dismiss="modal">
                            Later
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = new bootstrap.Modal(document.getElementById('pushPromptModal'));
    
    if (!document.getElementById('bell-animation-css')) {
        const style = document.createElement('style');
        style.id = 'bell-animation-css';
        style.innerHTML = 
            @keyframes ring {
                0% { transform: rotate(0); }
                10% { transform: rotate(15deg); }
                20% { transform: rotate(-10deg); }
                30% { transform: rotate(5deg); }
                40% { transform: rotate(-5deg); }
                50% { transform: rotate(0); }
            }
            .animate-bell {
                animation: ring 1.5s ease infinite;
                display: inline-block;
            }
        ;
        document.head.appendChild(style);
    }
    
    modal.show();
}

async function enablePushFromModal() {
    const modalEl = document.getElementById('pushPromptModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
    
    if (typeof subscribeToPush === 'function') {
        await subscribeToPush();
    }
}

// ═══════════════════════════════════════════════════════════════════
// Force PWA Installation Prompt (PC & Mobile)
// ═══════════════════════════════════════════════════════════════════
let deferredPrompt;

function isPWA() {
    return window.matchMedia('(display-mode: standalone)').matches || 
           window.navigator.standalone === true || 
           document.referrer.includes('android-app://');
}

window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the default browser prompt
    e.preventDefault();
    // Stash the event so it can be triggered later
    deferredPrompt = e;
    
    // Only prompt if not already running in PWA standalone mode
    if (!isPWA()) {
        // Wait 4 seconds after page load to show the install prompt
        setTimeout(() => {
            showPWAInstallModal();
        }, 4000);
    }
});

function showPWAInstallModal() {
    if (document.getElementById('pwaInstallModal')) return;

    const modalHTML = 
    <div class="modal fade" id="pwaInstallModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
        <div class="modal-dialog modal-dialog-centered" style="max-width: 400px; margin: 1.75rem auto;">
            <div class="modal-content" style="border-radius: 16px; border: none; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.15);">
                <div class="modal-body text-center p-4">
                    <div class="rounded-circle bg-primary bg-opacity-10 text-primary d-inline-flex align-items-center justify-content-center mb-3" style="width: 64px; height: 64px;">
                        <i class="bi bi-laptop fs-3"></i>
                    </div>
                    <h5 class="fw-bold mb-2">Install CA Manage</h5>
                    <p class="text-muted small px-2">Install our app on your computer or mobile device for a faster, full-screen experience and secure offline access.</p>
                    <div class="d-flex flex-column gap-2 mt-4">
                        <button class="btn btn-primary w-100 py-2 fw-medium btn-sm" onclick="triggerPWAInstall()">
                            Install Application
                        </button>
                        <button class="btn btn-link text-muted btn-sm text-decoration-none" data-bs-dismiss="modal">
                            Use in Browser
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = new bootstrap.Modal(document.getElementById('pwaInstallModal'));
    modal.show();
}

async function triggerPWAInstall() {
    const modalEl = document.getElementById('pwaInstallModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();

    if (!deferredPrompt) return;
    
    // Show the browser install prompt
    deferredPrompt.prompt();
    
    // Wait for the user to respond to the prompt
    const { outcome } = await deferredPrompt.userChoice;
    console.log([PWA] Install prompt outcome: );
    
    // Clear the deferred prompt variable
    deferredPrompt = null;
}
