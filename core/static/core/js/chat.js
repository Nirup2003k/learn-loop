const chatBox = document.getElementById('chatBox');
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    const input = document.getElementById('messageInput');
    const form = document.getElementById('chatForm');
    
    const chatDataEl = document.getElementById('chatData');
    let lastMessageId = parseInt(chatDataEl.getAttribute('data-last-msg-id')) || 0;
    const currentUserId = parseInt(chatDataEl.getAttribute('data-current-user-id'));
    const otherUserId = parseInt(chatDataEl.getAttribute('data-other-user-id'));
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    function appendMessage(msgData, isSent) {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'msg-row ' + (isSent ? 'sent' : 'received');
        rowDiv.setAttribute('data-id', msgData.id);

        rowDiv.innerHTML = `
            <div class="msg-bubble">
                <div>${msgData.content}</div>
                <div class="msg-time">${msgData.timestamp}</div>
            </div>
        `;

        chatBox.appendChild(rowDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
        lastMessageId = Math.max(lastMessageId, msgData.id);
    }

    // Handle AJAX form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const content = input.value.trim();
        if (content === '') return;

        input.value = ''; // clear immediately

        fetch(`/chats/${otherUserId}/send/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ message: content })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                appendMessage(data.message, true);
            }
        })
        .catch(err => console.error('Error sending message:', err));
    });

    // Enter key support
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            form.dispatchEvent(new Event('submit'));
        }
    });

    // AJAX Polling every 3 seconds
    setInterval(function() {
        fetch(`/chats/${otherUserId}/get/${lastMessageId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    if (msg.id > lastMessageId) {
                        const isSent = (msg.sender_id === currentUserId);
                        appendMessage(msg, isSent);
                    }
                });
            }
        })
        .catch(err => console.error('Error fetching messages:', err));
    }, 3000);