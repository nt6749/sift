#!/bin/bash

echo "🚀 Starting SIFT Medical Policy Analyzer..."

# Function to gracefully stop both servers when the script is terminated
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Services stopped."
    exit 0
}

# Catch Ctrl+C and call the cleanup function
trap cleanup SIGINT SIGTERM

# 1. Start the Backend
echo "⚙️  Starting Backend..."
cd AI_Parser || exit
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi
python app.py &
BACKEND_PID=$!
cd ..

# 2. Start the Frontend
echo "💻 Starting Frontend..."
cd frontend || exit
npm run dev &
FRONTEND_PID=$!
cd ..

# 3. Wait a few seconds for services to boot up
echo "⏳ Waiting for servers to initialize..."
sleep 5

# 4. Open the browser
echo "🌐 Opening http://localhost:3000..."
if command -v open > /dev/null; then
    open http://localhost:3000
elif command -v xdg-open > /dev/null; then
    xdg-open http://localhost:3000
elif command -v start > /dev/null; then
    start http://localhost:3000
else
    echo "Please open http://localhost:3000 manually."
fi

echo "✨ SIFT is running! Press Ctrl+C to shut down both servers."

# Wait for the processes so the script doesn't exit immediately
wait $BACKEND_PID $FRONTEND_PID