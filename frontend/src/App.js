import React, { useState, useEffect } from "react";
import "./App.css";
import ChatWindow from "./components/ChatWindow";
import { getSystemStatus, getSampleQueries } from "./api/api";

function App() {
  const [systemStatus, setSystemStatus] = useState({ status: 'connecting', components: {} });
  const [sampleQueries, setSampleQueries] = useState([]);
  const [darkMode, setDarkMode] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    // Check for saved dark mode preference
    const savedDarkMode = localStorage.getItem('partselect-dark-mode');
    if (savedDarkMode) {
      const isDark = JSON.parse(savedDarkMode);
      setDarkMode(isDark);
      document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    }

    // Fetch system status and sample queries on load
    const fetchInitialData = async () => {
      try {
        setSystemStatus({ status: 'connecting', components: {} });
        const [status, samples] = await Promise.all([
          getSystemStatus(),
          getSampleQueries()
        ]);
        setSystemStatus(status);
        setSampleQueries(samples);
        setRetryCount(0); // Reset retry count on success
      } catch (error) {
        console.error('Error fetching initial data:', error);
        setSystemStatus({ status: 'error', components: {} });
      }
    };

    fetchInitialData();

    // Set up periodic status check with exponential backoff retry
    const checkSystemStatus = async () => {
      try {
        const status = await getSystemStatus();
        setSystemStatus(status);
        // Reset retry count on successful response (even if unhealthy)
        if (status.status === 'healthy' || status.status === 'unhealthy') {
          setRetryCount(0);
        }
      } catch (error) {
        console.error('Error checking system status:', error);
        setSystemStatus({ status: 'error', components: {} });
        setRetryCount(prev => prev + 1);
      }
    };

    // Check status every 30 seconds, but with exponential backoff if errors
    // Don't retry if backend is responding but unhealthy (it's a backend code issue, not connection issue)
    const interval = setInterval(() => {
      if (retryCount < 5 && systemStatus?.status !== 'unhealthy') { 
        checkSystemStatus();
      }
    }, Math.min(30000 * Math.pow(2, retryCount), 300000)); // Max 5 minutes

    return () => clearInterval(interval);
  }, [retryCount]);

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('partselect-dark-mode', JSON.stringify(newDarkMode));
    document.documentElement.setAttribute('data-theme', newDarkMode ? 'dark' : 'light');
  };

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <div className="logo-container">
            <img src="/ps_image.svg" alt="PartSelect" className="logo" />
            <div className="title-container">
              <h1 className="app-title">PartSelect AI Assistant</h1>
              <p className="app-subtitle">Expert help for refrigerator and dishwasher parts</p>
            </div>
          </div>
                <div className="header-controls">
        <a 
          href="tel:1-866-319-8402" 
          className="phone-btn"
          title="Call Customer Service"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          1-866-319-8402
        </a>

        <a 
          href="mailto:CustomerService@PartSelect.com" 
          className="contact-us-btn"
          title="Contact Customer Service"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <polyline points="22,6 12,13 2,6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Contact Us
        </a>

        <button
          className="dark-mode-toggle"
          onClick={toggleDarkMode}
          title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {darkMode ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="2"/>
              <path d="m12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          )}
        </button>
        

      </div>
        </div>
      </header>
      
      <div className="status-indicator-bottom">
        <div className={`status-dot ${
          systemStatus?.status === 'healthy' ? 'healthy' : 
          systemStatus?.status === 'connecting' ? 'connecting' : 
          'error'
        }`}></div>
        <span className="status-text">
          {systemStatus?.status === 'healthy' ? 'System Online' : 
           systemStatus?.status === 'connecting' ? 'Connecting...' : 
           systemStatus?.status === 'unhealthy' ? 'Backend Error' :
           retryCount >= 5 ? 'System Offline' : 
           'Connection Error - Retrying...'}
        </span>
      </div>

      <main className="main-content">
        <ChatWindow sampleQueries={sampleQueries} />
      </main>
      
    </div>
  );
}

export default App;
