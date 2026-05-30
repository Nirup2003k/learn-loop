const chatBox = document.getElementById('chatBox');
if (chatBox) {
    chatBox.scrollTop = chatBox.scrollHeight;
}

const input = document.getElementById('messageInput');
const form = document.getElementById('chatForm');

const chatDataEl = document.getElementById('chatData');
if (!chatDataEl) {
    console.warn('Chat data element not found.');
} else {
    var lastMessageId = parseInt(chatDataEl.getAttribute('data-last-msg-id')) || 0;
    var currentUserId = parseInt(chatDataEl.getAttribute('data-current-user-id'));
    var otherUserId = parseInt(chatDataEl.getAttribute('data-other-user-id'));
}

function appendMessage(msgData, isSent) {
    // Prevent duplicate messages
    if (msgData.id <= lastMessageId && lastMessageId !== 0) return;
    
    const rowDiv = document.createElement('div');
    rowDiv.className = 'msg-row ' + (isSent ? 'sent' : 'received');
    rowDiv.setAttribute('data-id', msgData.id);

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'msg-bubble';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';
    contentDiv.textContent = msgData.content;

    const timeDiv = document.createElement('div');
    timeDiv.className = 'msg-time';
    timeDiv.textContent = msgData.timestamp;

    bubbleDiv.appendChild(contentDiv);
    bubbleDiv.appendChild(timeDiv);
    rowDiv.appendChild(bubbleDiv);

    chatBox.appendChild(rowDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    lastMessageId = Math.max(lastMessageId, msgData.id);
    
    // Hide empty state if present
    const emptyState = document.querySelector('.chat-empty');
    if (emptyState) emptyState.style.display = 'none';
}

function fetchMessages() {
    if (!otherUserId) return;
    
    fetch(`/chats/${otherUserId}/get/${lastMessageId}/`)
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                data.messages.forEach(msg => {
                    const isSent = (msg.sender_id === currentUserId);
                    appendMessage(msg, isSent);
                });
            }
        })
        .catch(err => console.error('Error fetching messages:', err));
}

// Start AJAX polling for chat messages every 3 seconds
setInterval(fetchMessages, 3000);

form.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const content = input.value.trim();
    if (content === '') return;

    input.value = ''; // clear immediately
    
    // Get CSRF token from cookies
    const getCookie = (name) => {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };

    fetch(`/chats/${otherUserId}/send/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ message: content })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const isSent = (data.message.sender_id === currentUserId);
            appendMessage(data.message, isSent);
        }
    })
    .catch(err => console.error('Error sending message:', err));
});

input.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        form.dispatchEvent(new Event('submit'));
    }
});
