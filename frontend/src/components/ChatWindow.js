import React, { useState, useEffect, useRef } from "react";
import "./ChatWindow.css";
import { getAIMessage } from "../api/api";
import { marked } from "marked";

function ChatWindow({ sampleQueries = [] }) {
  const [typewriterText, setTypewriterText] = useState("");
  const [showCapabilities, setShowCapabilities] = useState([]);
  const [typewriterComplete, setTypewriterComplete] = useState(false);
  const [showQuestion, setShowQuestion] = useState(false);
  const defaultMessage = [{
    role: "assistant",
    content: "Welcome to PartSelect AI Assistant. I specialize in refrigerator and dishwasher parts and can help you with:",
    isWelcome: true,
    capabilities: [
      "Finding the right appliance parts",
      "Checking part compatibility", 
      "Troubleshooting common issues",
      "Installation guidance"
    ]
  }];

  const [messages, setMessages] = useState(defaultMessage);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSamples, setShowSamples] = useState(true);
  const [lastUserMessage, setLastUserMessage] = useState("");

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
      scrollToBottom();
  }, [messages]);

  // Typewriter effect for welcome message
  useEffect(() => {
    if (messages.length > 0 && messages[0].isWelcome && showSamples) {
      const fullText = messages[0].content;
      let currentIndex = 0;
      let typeInterval;
      let capInterval;
      
      typeInterval = setInterval(() => {
        if (currentIndex <= fullText.length) {
          setTypewriterText(fullText.slice(0, currentIndex));
          currentIndex++;
        } else {
          clearInterval(typeInterval);
          setTypewriterComplete(true);
          
          // Start showing capabilities one by one after a small delay
          setTimeout(() => {
            const capabilities = messages[0].capabilities;
            console.log("Total capabilities:", capabilities.length);
            
            // Show all capabilities at once for now to debug
            setShowCapabilities([0, 1, 2, 3]);
            
            // Show question after capabilities
            setTimeout(() => {
              setShowQuestion(true);
            }, 100);
            
            /* Original animation code - commented out for debugging
            let capIndex = 0;
            
            capInterval = setInterval(() => {
              if (capIndex < capabilities.length) {
                console.log("Adding capability index:", capIndex);
                setShowCapabilities(prev => [...prev, capIndex]);
                capIndex++;
              } else {
                clearInterval(capInterval);
                // Show question after all capabilities are shown
                setTimeout(() => {
                  setShowQuestion(true);
                }, 200);
              }
            }, 20);
            */
          }, 100);
        }
      }, 25);

      return () => {
        if (typeInterval) clearInterval(typeInterval);
        if (capInterval) clearInterval(capInterval);
      };
    }
  }, [messages, showSamples]);

  const handleSend = async (inputText = input, isRegenerate = false) => {
    const messageText = inputText.trim();
    if (messageText === "" || isLoading) return;

    // Hide sample queries after first message
    if (showSamples) {
      setShowSamples(false);
    }

    // Store the user message for regenerate functionality
    if (!isRegenerate) {
      setLastUserMessage(messageText);
      // Add user message
      const userMessage = { role: "user", content: messageText };
      setMessages(prevMessages => [...prevMessages, userMessage]);
      setInput("");
    } else {
      // For regenerate, remove the last assistant message
      setMessages(prevMessages => {
        const filteredMessages = prevMessages.filter((msg, index) => {
          if (index === prevMessages.length - 1 && msg.role === "assistant") {
            return false;
          }
          return true;
        });
        return filteredMessages;
      });
    }

    setIsLoading(true);

    try {
      // Add loading message
      const loadingMessage = { role: "assistant", content: "", isLoading: true };
      setMessages(prevMessages => [...prevMessages, loadingMessage]);

      // Call API
      const newMessage = await getAIMessage(messageText);
      
      // Replace loading message with actual response
      setMessages(prevMessages => 
        prevMessages.slice(0, -1).concat([newMessage])
      );
    } catch (error) {
      console.error('Error sending message:', error);
      // Replace loading message with error
      setMessages(prevMessages => 
        prevMessages.slice(0, -1).concat([{
          role: "assistant",
          content: "I'm sorry, I encountered an error. Please try again."
        }])
      );
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleNewChat = () => {
    setMessages(defaultMessage);
    setShowSamples(true);
    setLastUserMessage("");
    setInput("");
    setTypewriterText("");
    setShowCapabilities([]);
    setTypewriterComplete(false);
    setShowQuestion(false);
    // Clear the stored thread ID to start a new conversation
    localStorage.removeItem('partselect-thread-id');
    inputRef.current?.focus();
  };

  const handleRegenerate = () => {
    if (lastUserMessage && !isLoading) {
      handleSend(lastUserMessage, true);
    }
  };

  const handleSampleQuery = (query) => {
    setInput(query);
    inputRef.current?.focus();
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey && !isLoading) {
      e.preventDefault();
      handleSend();
    }
  };

  const processLinksInHTML = (html) => {
    // Replace all <a> tags to open in new tab and add external link icon
    return html.replace(
      /<a\s+href="([^"]*)"[^>]*>(.*?)<\/a>/gi,
      '<a href="$1" target="_blank" rel="noopener noreferrer" class="external-link">$2<svg class="external-link-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><polyline points="15,3 21,3 21,9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><line x1="10" y1="14" x2="21" y2="3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></a>'
    );
  };

  const renderMessage = (message, index) => {
    if (message.isLoading) {
      return (
        <div key={index} className="assistant-message-container">
          <div className="message assistant-message loading">
            <div className="typing-indicator">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
            <span className="typing-text">AI is thinking...</span>
          </div>
        </div>
      );
    }

    const isLastAssistantMessage = message.role === "assistant" && 
                                   index === messages.length - 1 && 
                                   canRegenerate;

  return (
      <div key={index} className={`${message.role}-message-container ${message.isWelcome ? 'welcome-container' : ''}`}>
                  {message.content && (
          <div className={`message ${message.role}-message ${message.isWelcome ? 'welcome-message' : ''}`}>
                                    {message.isWelcome ? (
                          <div className="welcome-content">
                            <p className="welcome-intro">
                              {typewriterText}
                              {!typewriterComplete && <span className="typewriter-cursor">|</span>}
                            </p>
                            
                            <div className="capabilities-grid">
                              {message.capabilities?.map((capability, index) => (
                                <div 
                                  key={index} 
                                  className={`capability-item ${showCapabilities.includes(index) ? 'capability-visible' : 'capability-hidden'}`}
                                >
                                  <div className="capability-icon">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                      <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                    </svg>
                                  </div>
                                  <span>{capability}</span>
                                </div>
                              ))}
                            </div>
                            
                                        {showQuestion && (
              <p className="welcome-question">What can I help you with today?</p>
            )}
                          </div>
                        ) : (
              <div 
                dangerouslySetInnerHTML={{
                  __html: processLinksInHTML(marked(message.content).replace(/<p>|<\/p>/g, ""))
                }}
              />
            )}

            {message.intent && message.confidence && (
              <div className="message-metadata">
                <span className="intent">Intent: {message.intent}</span>
                <span className="confidence">Confidence: {(message.confidence * 100).toFixed(0)}%</span>
              </div>
            )}
                      </div>
                  )}
        
        {isLastAssistantMessage && (
          <button 
            className="regenerate-btn-inline" 
            onClick={handleRegenerate}
            disabled={isLoading}
            title="Regenerate response"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M1 4V10H7M23 20V14H17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14L18.36 18.36A9 9 0 0 1 3.51 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Regenerate
          </button>
        )}
      </div>
    );
  };

  // Check if we can show regenerate button
  const canRegenerate = lastUserMessage && messages.length > 1 && 
                        messages[messages.length - 1].role === "assistant" && !isLoading;

  return (
    <div className="chat-container">
      <div className="messages-container">
        {messages.map((message, index) => renderMessage(message, index))}
        
        {showSamples && sampleQueries.length > 0 && (
          <div className="sample-queries-container">
            <h3 className="sample-queries-title">Try asking about:</h3>
            <div className="sample-queries-grid">
              {sampleQueries.slice(0, 3).map((category, catIndex) => (
                <div key={catIndex} className="sample-category">
                  <h4 className="category-title">{category.category}</h4>
                  {category.queries.slice(0, 2).map((query, queryIndex) => (
                    <button
                      key={queryIndex}
                      className="sample-query-btn"
                      onClick={() => handleSampleQuery(query)}
                      disabled={isLoading}
                    >
                      {query}
                    </button>
                  ))}
              </div>
          ))}
            </div>
          </div>
        )}
        
          <div ref={messagesEndRef} />
      </div>
      
          <div className="input-area">
            <button
              className="control-btn new-chat-btn-bottom"
              onClick={handleNewChat}
              disabled={isLoading}
              title="Start a new conversation"
            >
              <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg" className="icon" aria-hidden="true">
                <path d="M2.6687 11.333V8.66699C2.6687 7.74455 2.66841 7.01205 2.71655 6.42285C2.76533 5.82612 2.86699 5.31731 3.10425 4.85156L3.25854 4.57617C3.64272 3.94975 4.19392 3.43995 4.85229 3.10449L5.02905 3.02149C5.44666 2.84233 5.90133 2.75849 6.42358 2.71582C7.01272 2.66769 7.74445 2.66797 8.66675 2.66797H9.16675C9.53393 2.66797 9.83165 2.96586 9.83179 3.33301C9.83179 3.70028 9.53402 3.99805 9.16675 3.99805H8.66675C7.7226 3.99805 7.05438 3.99834 6.53198 4.04102C6.14611 4.07254 5.87277 4.12568 5.65601 4.20313L5.45581 4.28906C5.01645 4.51293 4.64872 4.85345 4.39233 5.27149L4.28979 5.45508C4.16388 5.7022 4.08381 6.01663 4.04175 6.53125C3.99906 7.05373 3.99878 7.7226 3.99878 8.66699V11.333C3.99878 12.2774 3.99906 12.9463 4.04175 13.4688C4.08381 13.9833 4.16389 14.2978 4.28979 14.5449L4.39233 14.7285C4.64871 15.1465 5.01648 15.4871 5.45581 15.7109L5.65601 15.7969C5.87276 15.8743 6.14614 15.9265 6.53198 15.958C7.05439 16.0007 7.72256 16.002 8.66675 16.002H11.3337C12.2779 16.002 12.9461 16.0007 13.4685 15.958C13.9829 15.916 14.2976 15.8367 14.5447 15.7109L14.7292 15.6074C15.147 15.3511 15.4879 14.9841 15.7117 14.5449L15.7976 14.3447C15.8751 14.128 15.9272 13.8546 15.9587 13.4688C16.0014 12.9463 16.0017 12.2774 16.0017 11.333V10.833C16.0018 10.466 16.2997 10.1681 16.6667 10.168C17.0339 10.168 17.3316 10.4659 17.3318 10.833V11.333C17.3318 12.2555 17.3331 12.9879 17.2849 13.5771C17.2422 14.0993 17.1584 14.5541 16.9792 14.9717L16.8962 15.1484C16.5609 15.8066 16.0507 16.3571 15.4246 16.7412L15.1492 16.8955C14.6833 17.1329 14.1739 17.2354 13.5769 17.2842C12.9878 17.3323 12.256 17.332 11.3337 17.332H8.66675C7.74446 17.332 7.01271 17.3323 6.42358 17.2842C5.90135 17.2415 5.44665 17.1577 5.02905 16.9785L4.85229 16.8955C4.19396 16.5601 3.64271 16.0502 3.25854 15.4238L3.10425 15.1484C2.86697 14.6827 2.76534 14.1739 2.71655 13.5771C2.66841 12.9879 2.6687 12.2555 2.6687 11.333ZM13.4646 3.11328C14.4201 2.334 15.8288 2.38969 16.7195 3.28027L16.8865 3.46485C17.6141 4.35685 17.6143 5.64423 16.8865 6.53613L16.7195 6.7207L11.6726 11.7686C11.1373 12.3039 10.4624 12.6746 9.72827 12.8408L9.41089 12.8994L7.59351 13.1582C7.38637 13.1877 7.17701 13.1187 7.02905 12.9707C6.88112 12.8227 6.81199 12.6134 6.84155 12.4063L7.10132 10.5898L7.15991 10.2715C7.3262 9.53749 7.69692 8.86241 8.23218 8.32715L13.2791 3.28027L13.4646 3.11328ZM15.7791 4.2207C15.3753 3.81702 14.7366 3.79124 14.3035 4.14453L14.2195 4.2207L9.17261 9.26856C8.81541 9.62578 8.56774 10.0756 8.45679 10.5654L8.41772 10.7773L8.28296 11.7158L9.22241 11.582L9.43433 11.543C9.92426 11.432 10.3749 11.1844 10.7322 10.8271L15.7791 5.78027L15.8552 5.69629C16.185 5.29194 16.1852 4.708 15.8552 4.30371L15.7791 4.2207Z"></path>
              </svg>
            </button>
            <div className="input-container">
            <input
                ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about refrigerator or dishwasher parts..."
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                className="message-input"
              />
              <button
                className="send-button"
                onClick={() => handleSend()}
                disabled={isLoading || input.trim() === ""}
              >
                {isLoading ? (
                  <div className="send-loading">
                    <div className="send-spinner"></div>
                  </div>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M2 21L23 12L2 3V10L17 12L2 14V21Z" fill="currentColor"/>
                  </svg>
                )}
            </button>
            </div>
          </div>

                  {/* Floating Menu Button */}
          <div className="floating-help-button">
            <div className="help-button-trigger">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <div className="help-dropdown">
              <div className="help-option">
                <a href="https://www.partselect.com/user/self-service/" target="_blank" rel="noopener noreferrer" className="help-link">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M12 7v5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    <path d="M7 9.5v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                    <path d="M17 9.5v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                  <span>Find My Order</span>
                </a>
              </div>
              <div className="help-option">
                <a href="https://www.partselect.com/Help/#Returns" target="_blank" rel="noopener noreferrer" className="help-link">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <polyline points="1,9 1,2 8,2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="m3 11a9 9 0 1 0 2.12-6.36l-6.12 6.36" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  <span>Return Policy</span>
                </a>
              </div>
              <div className="help-option">
                <a href="https://www.partselect.com/Same-Day-Shipping.htm#:~:text=or%20part%20number-,Same%2Dday%20Shipping,-All%20Original%20Manufacturer" target="_blank" rel="noopener noreferrer" className="help-link">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="1" y="3" width="15" height="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="m16 8 4-4-4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="m20 4h-7a4 4 0 0 0 0 8h1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  <span>Same Day Shipping</span>
                </a>
              </div>

              <div className="help-option">
                <a href="https://www.partselect.com/One-Year-Warranty.htm#:~:text=Original%20Manufacturer%20Parts-,1%20Year%20Warranty,-Appliance%20Parts" target="_blank" rel="noopener noreferrer" className="help-link">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  <span>1 Year Warranty</span>
                </a>
              </div>
            </div>
          </div>
      </div>
);
}

export default ChatWindow;
