// --- Dark Mode Logic ---
document.addEventListener('DOMContentLoaded', () => {

    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;

    if (!themeToggle) {
        console.error("Theme toggle button missing!");
        return;
    }

    function setTheme(theme) {
        body.setAttribute('data-bs-theme', theme);

        // update toggle button text
        themeToggle.innerHTML = theme === "dark" ? "☀️ Light Mode" : "🌙 Dark Mode";

        localStorage.setItem('theme', theme);
    }

    function initializeTheme() {
        const stored = localStorage.getItem('theme');

        if (stored) {
            setTheme(stored);
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            setTheme("dark");
        } else {
            setTheme("light");
        }
    }

    themeToggle.addEventListener('click', () => {
        const current = body.getAttribute('data-bs-theme');
        setTheme(current === "light" ? "dark" : "light");
    });

    initializeTheme();
});
// --- End Dark Mode Logic ---


document.addEventListener('DOMContentLoaded', () => {
    // --- Chat Bot Elements ---
    const chatToggleBtn = document.getElementById('chat-toggle-btn');
    const chatCloseBtn = document.getElementById('chat-close-btn');
    const chatWindow = document.getElementById('chat-window');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatMessages = document.getElementById('chat-messages');
    
    // --- Helpers ---
    const isChatWindowVisible = () => chatWindow.style.display !== 'none';

    // Scroll to the bottom of the chat window
    const scrollToBottom = () => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    // Toggle Visibility
    if (chatToggleBtn && chatWindow) {
        chatToggleBtn.addEventListener('click', () => {
            chatWindow.style.display = isChatWindowVisible() ? 'none' : 'flex';
            if (isChatWindowVisible()) {
                chatInput.focus();
                scrollToBottom();
            }
        });
    }

    // Close Button
    if (chatCloseBtn) {
        chatCloseBtn.addEventListener('click', () => {
            chatWindow.style.display = 'none';
        });
    }

    // Input Validation (Enable/Disable Send button)
    if (chatInput && chatSendBtn) {
        chatInput.addEventListener('input', () => {
            chatSendBtn.disabled = chatInput.value.trim() === '';
        });
    }

    // Function to display a message
    const displayMessage = (message, sender) => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add(sender === 'user' ? 'user-message' : 'mentor-message');
        const htmlContent = convertMarkdownToHtml(message); 
        messageDiv.innerHTML = htmlContent;
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    };

    const convertMarkdownToHtml = (text) => {
    // 1. Convert bold (**text**) to <strong>
    let html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // 2. Convert ordered list (1. Item) to <ol><li>...</li></ol>
    // This is complex and assumes the model is consistent.
    // For simplicity, let's focus on converting it to an unordered list if it starts with numbers/bullets.
    
    // Convert numbered lists starting at the beginning of a line (e.g., 1., 2.) to <ul><li>
    html = html.replace(/^(\d+\.\s)(.*)/gm, '<li>$2</li>');
    
    // Wrap the entire list in an <ol> tag if list items were created
    if (html.includes('<li>')) {
        // Simple heuristic: If it contains list items, wrap the text block
        const lines = html.split('\n').filter(line => line.trim() !== '');
        let newHtml = '';
        let inList = false;

        lines.forEach(line => {
            if (line.startsWith('<li>')) {
                if (!inList) {
                    newHtml += '<ol>';
                    inList = true;
                }
                newHtml += line;
            } else {
                if (inList) {
                    newHtml += '</ol>';
                    inList = false;
                }
                newHtml += '<p>' + line + '</p>';
            }
        });
        if (inList) newHtml += '</ol>';
        return newHtml;
    }

    return html.replace(/\n/g, '<br>'); // Default line breaks
};

    // Main Chat Submission Function
    const sendMessage = async () => {
        const message = chatInput.value.trim();
        if (message === '') return;

        displayMessage(message, 'user');
        chatInput.value = ''; // Clear input immediately
        chatSendBtn.disabled = true;

        // Show a loading indicator (optional, but good UX)
        const loadingIndicator = document.createElement('div');
        loadingIndicator.classList.add('mentor-message', 'small', 'text-muted');
        loadingIndicator.id = 'loading-mentor';
        loadingIndicator.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Thinking...';
        chatMessages.appendChild(loadingIndicator);
        scrollToBottom();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            });

            // Remove loading indicator
            chatMessages.removeChild(loadingIndicator);

            if (response.ok) {
                const data = await response.json();
                displayMessage(data.response, 'mentor');
            } else {
                const errorData = await response.json();
                displayMessage(`Error: ${errorData.error || 'Failed to get response.'}`, 'mentor');
            }
        } catch (error) {
            console.error('Fetch error:', error);
            // Remove loading indicator on failure
            const existingLoading = document.getElementById('loading-mentor');
            if (existingLoading) chatMessages.removeChild(existingLoading);
            displayMessage('Connection error. Please try again.', 'mentor');
        }
        
        chatInput.focus();
    };

    // Event Listeners for Send
    if (chatSendBtn) {
        chatSendBtn.addEventListener('click', sendMessage);
    }
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
});


//notification badge update

// static/scripts.js (Add this at the end of the file)

function fetchNotificationCount() {
    const notifBadge = document.getElementById('notif-badge');
    if (!notifBadge) return;

    fetch('/api/notifications/count')
        .then(response => response.json())
        .then(data => {
            const count = data.count;
            if (count > 0) {
                notifBadge.textContent = count > 99 ? '99+' : count;
                notifBadge.style.display = 'block';
            } else {
                notifBadge.style.display = 'none';
            }
        })
        .catch(error => console.error('Error fetching notification count:', error));
}

// 🚨 Start fetching count when the page loads
fetchNotificationCount();
// 🚨 Poll every 30 seconds to keep the count updated (optional, but good UX)
setInterval(fetchNotificationCount, 30000);