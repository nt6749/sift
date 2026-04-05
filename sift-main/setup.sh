#!/bin/bash

# Medical Policy Extraction - Setup Script
# This script sets up both backend and frontend

set -e

echo "🚀 Medical Policy Extraction - Setup Script"
echo "==========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Node.js
echo -e "${BLUE}Checking Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Node.js not found. Please install Node.js 16+${NC}"
    echo "Download from: https://nodejs.org/"
    exit 1
fi
echo -e "${GREEN}✓ Node.js $(node -v)${NC}"
echo ""

# Check Python
echo -e "${BLUE}Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python not found. Please install Python 3.8+${NC}"
    echo "Download from: https://www.python.org/"
    exit 1
fi
echo -e "${GREEN}✓ Python $(python3 --version)${NC}"
echo ""

# Setup Backend
echo -e "${BLUE}Setting up Backend...${NC}"
cd AI_Parser || exit

if [ ! -f "key.env" ]; then
    echo -e "${YELLOW}⚠️  key.env not found${NC}"
    echo "Please create key.env with your Google Gemini API key:"
    echo ""
    echo "  GEMINI_API_KEY=your_api_key_here"
    echo ""
    echo "Get your API key from: https://ai.google.dev/"
    read -p "Press Enter to continue..."
fi

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null || true

echo "Installing Python dependencies..."
pip install -q -r requirements.txt

echo -e "${GREEN}✓ Backend setup complete${NC}"
cd ..
echo ""

# Setup Frontend
echo -e "${BLUE}Setting up Frontend...${NC}"
cd frontend || exit

echo "Installing Node dependencies..."
npm install -q

echo -e "${GREEN}✓ Frontend setup complete${NC}"
cd ..
echo ""

# Summary
echo -e "${GREEN}==========================================="
echo "✓ Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit AI_Parser/key.env with your Google Gemini API key"
echo ""
echo "2. Start the backend (in Terminal 1):"
echo "   cd AI_Parser"
echo "   source venv/bin/activate  # or: . venv/Scripts/activate"
echo "   python app.py"
echo ""
echo "3. Start the frontend (in Terminal 2):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "4. Open http://localhost:3000 in your browser"
echo ""
echo "For more help, see QUICKSTART.md"
