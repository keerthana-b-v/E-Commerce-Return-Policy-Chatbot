const API_URL = 'http://127.0.0.1:8000';

const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const chatMessages = document.getElementById('chatMessages');
const customerNameInput = document.getElementById('customerName');
const orderIdInput = document.getElementById('orderId');
const apiStatus = document.getElementById('apiStatus');
const statusDot = document.querySelector('.status-dot');
const sendBtn = document.getElementById('sendBtn');
const spinner = document.getElementById('spinner');
const btnText = sendBtn.querySelector('.btn-text');

// 1. Check API Connection Status on Load
async function checkApiStatus() {
    try {
        const response = await fetch(API_URL);
        if (response.ok) {
            apiStatus.textContent = 'Backend Online';
            statusDot.classList.remove('offline');
            statusDot.classList.add('online');
        } else {
            throw new Error('API down');
        }
    } catch (error) {
        apiStatus.textContent = 'Backend Offline';
        statusDot.classList.remove('online');
        statusDot.classList.add('offline');
    }
}

// Check status on load and poll every 10 seconds
checkApiStatus();
setInterval(checkApiStatus, 10000);

// 2. Append Message helper
function appendMessage(sender, text, avatarSymbol) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);

    const avatarDiv = document.createElement('div');
    avatarDiv.classList.add('avatar');
    avatarDiv.textContent = avatarSymbol;

    const wrapper = document.createElement('div');
    wrapper.classList.add('message-content-wrapper');

    const content = document.createElement('div');
    content.classList.add('message-content');
    
    // Support basic markdown bolding if present
    content.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    wrapper.appendChild(content);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(wrapper);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 3. Set loading state
function setLoading(isLoading) {
    if (isLoading) {
        sendBtn.disabled = true;
        btnText.style.display = 'none';
        spinner.style.display = 'block';
    } else {
        sendBtn.disabled = false;
        btnText.style.display = 'inline';
        spinner.style.display = 'none';
    }
}

// 4. Handle Chat Submit
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const query = userInput.value.trim();
    if (!query) return;

    const customerName = customerNameInput.value.trim() || 'John Doe';
    const orderId = orderIdInput.value.trim() || 'ORD-9921';

    // Reset input
    userInput.value = '';

    // Append User Message to Thread
    appendMessage('user', query, '👤');

    setLoading(true);

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                customer_name: customerName,
                order_id: orderId
            })
        });

        if (!response.ok) {
            throw new Error('Server returned an error');
        }

        const data = await response.json();
        
        // Append Assistant Message to Thread
        appendMessage('assistant', data.answer, '🤖');

    } catch (error) {
        console.error('Error calling chatbot API:', error);
        appendMessage('assistant', '⚠️ *System Error:* Failed to connect to the backend. Please ensure the FastAPI server is running.', '🤖');
    } finally {
        setLoading(false);
    }
});
