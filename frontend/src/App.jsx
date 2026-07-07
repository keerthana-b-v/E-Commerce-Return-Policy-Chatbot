import { useState, useEffect, useRef } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am your automated customer support assistant. How can I help you with your shipping, returns, or warranties today?'
    }
  ]);
  const [customerName, setCustomerName] = useState('John Doe');
  const [orderId, setOrderId] = useState('ORD-9921');
  const [userInput, setUserInput] = useState('');
  const [apiStatus, setApiStatus] = useState('Checking backend...');
  const [isOnline, setIsOnline] = useState(false);
  const [loading, setLoading] = useState(false);

  const chatMessagesEndRef = useRef(null);

  // Generate or retrieve persistent session ID
  const sessionIdRef = useRef('');
  useEffect(() => {
    let sessId = sessionStorage.getItem('chatSessionId');
    if (!sessId) {
      sessId = 'sess-' + Math.random().toString(36).substring(2, 9) + '-' + Date.now().toString(36);
      sessionStorage.setItem('chatSessionId', sessId);
    }
    sessionIdRef.current = sessId;
  }, []);

  // Check API Status on load and poll every 10 seconds
  useEffect(() => {
    async function checkApiStatus() {
      try {
        const response = await fetch(API_URL);
        if (response.ok) {
          setApiStatus('Backend Online');
          setIsOnline(true);
        } else {
          throw new Error('API down');
        }
      } catch (error) {
        setApiStatus('Backend Offline');
        setIsOnline(false);
      }
    }

    checkApiStatus();
    const interval = setInterval(checkApiStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  // Auto scroll to bottom of chat
  useEffect(() => {
    chatMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle Form Submit (SSE streaming)
  const handleSubmit = async (e) => {
    e.preventDefault();
    const query = userInput.trim();
    if (!query) return;

    setUserInput('');
    setLoading(true);

    // 1. Add User Message
    const userMessage = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMessage]);

    // 2. Add empty Assistant Message placeholder
    const assistantIndex = messages.length + 1; // index where it will land
    setMessages((prev) => [...prev, { role: 'assistant', content: 'Thinking...' }]);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: query,
          session_id: sessionIdRef.current,
          customer_name: customerName.trim() || 'John Doe',
          order_id: orderId.trim() || 'ORD-9921'
        })
      });

      if (!response.ok) {
        throw new Error('Server returned an error');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let fullText = '';
      let isFirstChunk = true;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Retain incomplete line
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;

          try {
            const jsonStr = trimmed.slice(6);
            const data = JSON.parse(jsonStr);

            if (data.error) {
              if (isFirstChunk) {
                fullText = `⚠️ Error: ${data.error}`;
                isFirstChunk = false;
              } else {
                fullText += `\n⚠️ Error: ${data.error}`;
              }
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { role: 'assistant', content: fullText };
                return copy;
              });
            } else if (data.content) {
              if (isFirstChunk) {
                fullText = data.content;
                isFirstChunk = false;
              } else {
                fullText += data.content;
              }
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { role: 'assistant', content: fullText };
                return copy;
              });
            }
          } catch (err) {
            console.warn('Failed to parse SSE data chunk:', err);
          }
        }
      }

    } catch (error) {
      console.error('Error calling chatbot API:', error);
      setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = { 
          role: 'assistant', 
          content: '⚠️ System Error: Failed to connect to the backend. Please ensure the FastAPI server is running.' 
        };
        return copy;
      });
    } finally {
      setLoading(false);
    }
  };

  // Helper to format basic markdown bolding to strong HTML tags
  const renderMessageContent = (text) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div className="app-container">
      {/* Sidebar for CRM Simulation */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="icon">🏢</span>
          <h2>Simulation Settings</h2>
        </div>
        <p className="sidebar-desc">These settings simulate enterprise CRM context injection into the AI prompt.</p>
        
        <div className="crm-section">
          <h3>Customer 360 Context</h3>
          <div className="input-group">
            <label htmlFor="customerName">Customer Name</label>
            <input 
              type="text" 
              id="customerName" 
              value={customerName} 
              onChange={(e) => setCustomerName(e.target.value)}
              placeholder="Enter customer name"
            />
          </div>
          <div className="input-group">
            <label htmlFor="orderId">Order ID</label>
            <input 
              type="text" 
              id="orderId" 
              value={orderId} 
              onChange={(e) => setOrderId(e.target.value)}
              placeholder="Enter order ID"
            />
          </div>
        </div>
        
        <div className="sidebar-footer">
          <p>Connected to FastAPI API</p>
          <div className="status-indicator">
            <span className={`status-dot ${isOnline ? 'online' : 'offline'}`}></span>
            <span id="apiStatus">{apiStatus}</span>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="chat-area">
        <header className="chat-header">
          <h1>🛍️ Customer Support Assistant (React)</h1>
          <p>Ask anything about shipping, returns, and product warranties.</p>
        </header>

        {/* Chat Message Thread */}
        <div className="chat-messages" id="chatMessages">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              <div className="avatar">{msg.role === 'assistant' ? '🤖' : '👤'}</div>
              <div className="message-content-wrapper">
                <div className="message-content">
                  {msg.content === 'Thinking...' ? (
                    <span className="streaming-placeholder">Thinking...</span>
                  ) : (
                    renderMessageContent(msg.content)
                  )}
                </div>
              </div>
            </div>
          ))}
          <div ref={chatMessagesEndRef} />
        </div>

        {/* Chat Input Panel */}
        <div className="chat-input-panel">
          <form id="chatForm" className="chat-form" onSubmit={handleSubmit}>
            <input 
              type="text" 
              id="userInput" 
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              placeholder="Ask a question (e.g., What is your return policy?)" 
              required 
              autoComplete="off"
              disabled={loading}
            />
            <button type="submit" id="sendBtn" disabled={loading}>
              {loading ? (
                <div className="spinner" id="spinner"></div>
              ) : (
                <span className="btn-text">Send</span>
              )}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}

export default App;
