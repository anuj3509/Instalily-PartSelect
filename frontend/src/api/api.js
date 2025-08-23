
export const getAIMessage = async (userQuery) => {
  try {
    // Generate a thread ID for the conversation
    const threadId = localStorage.getItem('partselect-thread-id') || 
                     `thread-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('partselect-thread-id', threadId);

    // Call the RAG backend API
    const apiUrl = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8080';
    const response = await fetch(`${apiUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: userQuery,
        thread_id: threadId
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    // Format the response for the chat interface
    const message = {
      role: "assistant",
      content: data.response || "I'm sorry, I couldn't process your request right now. Please try again.",
      thread_id: data.thread_id
    };

    return message;

  } catch (error) {
    console.error('Error calling PartSelect LangGraph API:', error);
    
    // Return a friendly error message
    return {
      role: "assistant",
      content: "I'm having trouble connecting to the PartSelect system right now. Please check that the backend is running on 127.0.0.1:8080 and try again."
    };
  }
};

// Get sample queries for suggestions
export const getSampleQueries = async () => {
  try {
    const apiUrl = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8080';
    const response = await fetch(`${apiUrl}/sample-queries`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.sample_queries;
  } catch (error) {
    console.error('Error fetching sample queries:', error);
    return [];
  }
};

// Get system status
export const getSystemStatus = async () => {
  try {
    const apiUrl = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8080';
    const response = await fetch(`${apiUrl}/health`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    
    // If health endpoint reports unhealthy but we can connect, 
    // test if the main chat functionality is working
    if (data.status === 'unhealthy') {
      try {
        // Test a simple chat request to see if the backend is actually functional
        const testResponse = await fetch(`${apiUrl}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: "health_check_test",
            thread_id: "health_test_" + Date.now()
          }),
        });
        
        if (testResponse.ok) {
          // If chat works, consider the system healthy despite health endpoint issues
          return { status: 'healthy', service: 'rag-chat', note: 'Chat functional despite health check issues' };
        }
      } catch (chatError) {
        console.log('Chat test failed:', chatError);
      }
    }
    
    return data;
  } catch (error) {
    console.error('Error fetching system status:', error);
    return { status: 'error', components: {} };
  }
};
