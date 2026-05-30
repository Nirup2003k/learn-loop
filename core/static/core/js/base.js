const themeToggle = document.getElementById('theme-toggle');
const iconLight = document.getElementById('theme-icon-light');
const iconDark = document.getElementById('theme-icon-dark');

// Check for saved theme preference or prefer-color-scheme
const currentTheme = localStorage.getItem('theme');

if (currentTheme) {
    document.documentElement.setAttribute('data-theme', currentTheme);
    if (currentTheme === 'dark') {
        iconDark.style.display = 'none';
        iconLight.style.display = 'block';
    }
} else {
    // Optional: check OS preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
        iconDark.style.display = 'none';
        iconLight.style.display = 'block';
    }
}

themeToggle.addEventListener('click', () => {
    let theme = document.documentElement.getAttribute('data-theme');
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
        iconDark.style.display = 'block';
        iconLight.style.display = 'none';
    } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        iconDark.style.display = 'none';
        iconLight.style.display = 'block';
    }
});

// Global Notification WebSocket
if (window.location.pathname !== '/login/' && window.location.pathname !== '/register/') {
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const notificationSocket = new WebSocket(
        wsProtocol + '://' + window.location.host + '/ws/notifications/'
    );

    notificationSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        
        // Update notification badge if exists
        const badge = document.querySelector('.nav-icon-link .notification-badge');
        if (!badge) {
            const navLink = document.querySelector('.nav-icon-link');
            if (navLink) {
                const newBadge = document.createElement('span');
                newBadge.className = 'notification-badge';
                navLink.appendChild(newBadge);
            }
        }
    };
    
    // Global Chat Notification Polling
    let lastGlobalMsgId = parseInt(localStorage.getItem('lastGlobalMsgId')) || 0;
    
    function showGlobalMessageToast(sender, message, senderId) {
        // Don't show toast if we are already in the chat with this user
        if (window.location.pathname.includes('/chats/' + senderId + '/')) {
            return;
        }
        
        const existingToast = document.getElementById('chat-popup-toast');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.id = 'chat-popup-toast';
        toast.className = 'chat-popup-toast';
        
        const preview = message.length > 50 ? message.substring(0, 50) + '...' : message;
        
        toast.innerHTML = `
            <div class="toast-sender">${sender}</div>
            <div class="toast-msg">${preview}</div>
        `;
        
        toast.onclick = function() {
            window.location.href = '/chats/' + senderId + '/';
        };
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            if (document.body.contains(toast)) {
                toast.classList.add('fade-out');
                setTimeout(() => {
                    if (document.body.contains(toast)) {
                        toast.remove();
                    }
                }, 300);
            }
        }, 3000);
    }

    function pollUnreadMessages() {
        fetch('/chats/unread-global/?last_id=' + lastGlobalMsgId)
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                if (data.status === 'success' && data.messages.length > 0) {
                    const latestMsg = data.messages[data.messages.length - 1];
                    
                    // Only show toast if the message is actually newer than what we've seen
                    if (latestMsg.id > lastGlobalMsgId) {
                        lastGlobalMsgId = latestMsg.id;
                        localStorage.setItem('lastGlobalMsgId', lastGlobalMsgId);
                        showGlobalMessageToast(latestMsg.sender, latestMsg.content, latestMsg.sender_id);
                    }
                }
            })
            .catch(error => console.error('Error polling unread messages:', error));
    }

    // Poll every 8 seconds
    setInterval(pollUnreadMessages, 8000);
    // Initial poll
    setTimeout(pollUnreadMessages, 2000);
}

// Global AJAX handler for Skill-Swap Requests (Send, Accept, Reject)
document.addEventListener('submit', function(e) {
    const form = e.target;
    if (form && form.tagName === 'FORM') {
        const action = form.getAttribute('action') || '';
        if (action.includes('/send-request/') || action.includes('/accept/') || action.includes('/reject/')) {
            // Avoid intercepting if it's not a swap request action (e.g. login)
            if (action.includes('/schedule/')) return; // schedule accept/reject has same structure, let's skip for now unless requested
            
            e.preventDefault();
            
            const csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
            const csrfToken = csrfInput ? csrfInput.value : '';
            
            const buttons = form.querySelectorAll('button[type="submit"]');
            buttons.forEach(b => { b.disabled = true; b.style.opacity = '0.5'; });
            
            fetch(action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(res => {
                if (res.redirected) {
                    window.location.href = res.url;
                    return null;
                }
                const contentType = res.headers.get("content-type");
                if (contentType && contentType.includes("application/json")) {
                    return res.json();
                } else {
                    throw new Error("Server returned a non-JSON response (likely an error page).");
                }
            })
            .then(data => {
                if (!data) return; // Handled by redirect
                
                if (data.status === 'success') {
                    if (action.includes('/send-request/')) {
                        const btn = form.querySelector('button');
                        if (btn) {
                            btn.textContent = 'Pending';
                            btn.style.backgroundColor = '#6b7280';
                            btn.style.color = '#ffffff';
                            btn.style.borderColor = '#6b7280';
                            btn.disabled = true;
                        }
                    } else if (action.includes('/accept/') || action.includes('/reject/')) {
                        const card = form.closest('.card, .match-card, .list-item, .request-card');
                        const actionContainer = form.parentElement;
                        const targetContainer = (actionContainer && (actionContainer.classList.contains('row-actions') || actionContainer.classList.contains('request-actions'))) 
                            ? actionContainer : form;
                        
                        if (action.includes('/reject/') && card) {
                            card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                            card.style.opacity = '0';
                            card.style.transform = 'scale(0.95)';
                            setTimeout(() => card.remove(), 300);
                        } else {
                            targetContainer.innerHTML = `<span style="color: #10b981; font-weight: 600; padding: 8px;">${action.includes('/accept/') ? 'Accepted ✓' : 'Rejected ✕'}</span>`;
                        }
                    }
                } else {
                    alert(data.message || 'Error processing request.');
                    buttons.forEach(b => { b.disabled = false; b.style.opacity = '1'; });
                }
            })
            .catch(err => {
                console.error('AJAX Error:', err);
                buttons.forEach(b => { b.disabled = false; b.style.opacity = '1'; });
            });
        }
    }
});

