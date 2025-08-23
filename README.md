# PartSelect AI Assistant - RAG-Powered Chatbot

## Project Overview

**PartSelect AI Assistant** is an intelligent chatbot powered by Retrieval-Augmented Generation (RAG) that provides real-time assistance for refrigerator and dishwasher parts, repairs, and troubleshooting. The system delivers accurate, up-to-date information with actual PartSelect product data, pricing, and repair guides.

### Key Features

- **Real-time Parts Search** with actual prices and availability
- **Troubleshooting Guides** with repair video links
- **Model Compatibility Checking** for accurate part matching
- **Educational Content** for maintenance and installation
- **Smart Query Routing** based on user intent
- **Cost-Efficient AI** with optimized RAG architecture

### Advanced Features

- **Context-Aware Responses** based on query type and intent
- **Smart Fallbacks** when primary data insufficient
- **Conversation Memory** with thread-based conversation management
- **Real URL Integration** to PartSelect product pages
- **Response Regeneration** for improved answer quality
- **Conversation Statistics** and management tools
- **Multi-turn Conversations** with context preservation

## User Interface

![PartSelect AI Assistant Interface](interface.png)

*Modern, user-friendly interface featuring categorized question suggestions, real-time chat capabilities, and quick access to customer service features*

The interface includes:
- **Smart Question Categories**: Part Search, Compatibility Check, and Troubleshooting
- **Real-time Chat**: Interactive conversation with the AI assistant
- **Quick Links**: Easy access to order tracking, returns, shipping, and warranty information
- **Responsive Design**: Clean, modern UI optimized for both desktop and mobile use

## System Architecture

### Architecture Diagram

![PartSelect RAG Architecture](partselect.png)

*Complete system architecture showing the optimized RAG flow from user query to response generation*

### Detailed Architecture

The system uses a **dual-database approach** with **2 LLM calls** for optimal performance:

1. **Query Analysis (LLM Call 1)**: DeepSeek API analyzes user intent and extracts key terms
2. **Primary Data Fetch**: Fast SQLite + FTS5 queries for exact matches
3. **Vector Enhancement**: ChromaDB semantic search when additional context needed
4. **Response Generation (LLM Call 2)**: Single LLM call with complete context

**Core Component**: `OptimizedRAGOrchestrator` - Main orchestrator that manages the entire RAG process

### Database Architecture

- **Primary Database**: SQLite + FTS5 for fast, structured queries
- **Vector Database**: ChromaDB with Voyage AI embeddings for semantic search
- **Data Sources**: 10,000+ parts, 50+ repair guides, 200+ blog articles

## Project Structure

```
Instalily-PartSelect/
├── backend/           # FastAPI backend with RAG agents
├── frontend/          # React frontend application
├── scraping/          # Web scraping tools for data collection
├── requirements.txt   # Main project dependencies
├── requirements-dev.txt # Development dependencies
└── README.md         # This file
```

## Prerequisites

- **Python 3.8+**
- **Node.js 16+**
- **SQLite 3.0+**
- **API Keys**: DeepSeek API, Voyage AI API
- **pip** (Python package manager)
- **npm** or **yarn** (Node.js package manager)

## Installation & Setup

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/anuj3509/Instalily-PartSelect.git
cd Instalily-PartSelect

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install all Python dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 3. Environment Configuration

```bash
# Copy environment template (if available)
cp .env.example .env

# Edit .env file with your API keys
DEEPSEEK_API_KEY=your_deepseek_api_key
VOYAGE_API_KEY=your_voyage_ai_api_key
OPENAI_API_KEY=your_openai_key_here
```

### 4. Database Setup

```bash
cd backend

# Initialize database with schema
python -c "from database.database_manager import PartSelectDatabase; db = PartSelectDatabase(); print('Database initialized')"

# Load sample data (if available)
python -c "from database.database_manager import PartSelectDatabase; db = PartSelectDatabase(); db.load_data_from_json()"
```

### 5. Vector Database Setup

```bash
cd backend

# Setup ChromaDB collections
python -c "from services.vector_store.setup import PartSelectVectorStore; vs = PartSelectVectorStore(); vs.setup_collections()"

# Ingest data into vector store
python services/vector_store/setup.py
```

## Running the Application

### Backend Server

```bash
cd backend

# Start FastAPI server
python rag_main.py

# Server will start on http://127.0.0.1:8080
# API documentation available at http://127.0.0.1:8080/docs
```

### Frontend Application

```bash
cd frontend

# Start React development server
npm start

# Frontend will open on http://localhost:3000
```

### Alternative: Run Both Simultaneously

```bash
# Terminal 1: Backend
cd backend && python rag_main.py

# Terminal 2: Frontend  
cd frontend && npm start
```

## Development Setup

### Code Quality Tools

```bash
# Format code
black backend/
isort backend/

# Lint code
flake8 backend/
mypy backend/

# Run tests
pytest backend/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install
```

## Testing the System

### Sample Queries to Test

1. **Part Search**: "I need a water filter for my refrigerator"
2. **Troubleshooting**: "My dishwasher is leaking water"
3. **Compatibility**: "What parts work with model GE GSS25GSHSS?"
4. **Educational**: "How to clean a dishwasher filter"

### Expected Responses

- Real part numbers and prices
- Actual PartSelect product URLs
- Repair video links when available
- Installation difficulty and time estimates
- Brand and model compatibility information

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Check if SQLite file exists
   ls backend/database/partselect.db
   
   # Reinitialize database
   python -c "from database.database_manager import PartSelectDatabase; db = PartSelectDatabase()"
   ```

2. **Vector Database Error**
   ```bash
   # Reinstall ChromaDB
   pip uninstall chromadb && pip install chromadb
   
   # Recreate vector collections
   python services/vector_store/setup.py
   ```

3. **API Key Issues**
   ```bash
   # Verify environment variables
   echo $DEEPSEEK_API_KEY
   echo $VOYAGE_API_KEY
   ```

4. **Frontend Connection Error**
   ```bash
   # Check backend is running on port 8080
   curl http://127.0.0.1:8080/health
   
   # Verify frontend API configuration in src/api/api.js
   ```

5. **Import Errors**: Make sure you're in the correct virtual environment
6. **Port Conflicts**: Change ports in uvicorn or npm start commands

### Dependencies Issues

- **ChromaDB**: May require specific Python version compatibility
- **Playwright**: Requires browser installation (`playwright install`)
- **SQLite**: Built-in to Python, no additional installation needed

## Support

For questions, issues, or contributions:

- **Issues**: [GitHub Issues](https://github.com/anuj3509/Instalily-PartSelect/issues)
- **Discussions**: [GitHub Discussions](https://github.com/anuj3509/Instalily-PartSelect/discussions)
- **Email**: [anujmpatel0000@gmail.com]

---

**Note**: This project uses a dual-database approach with SQLite for fast queries and ChromaDB for semantic search, optimized for cost-effective AI responses with minimal LLM calls.

