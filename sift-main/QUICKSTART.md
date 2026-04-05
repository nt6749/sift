# Quick Start Guide

## System Requirements

- Node.js 16+ (for frontend)
- Python 3.8+ (for backend)
- Google Gemini API key

## Backend Setup (5 minutes)

### Step 1: Install Python Dependencies

```bash
cd AI_Parser
pip install -r requirements.txt
```

### Step 2: Configure Google Gemini API

Create `AI_Parser/key.env`:

```env
GEMINI_API_KEY={YOUR_API_KEY} 
```
#(ps: YOUR_API_KEY means you put your actual GEMINI api key inside. 
Get your API key from: https://ai.google.dev/

### Step 3: Start Backend Server

```bash
python app.py
```

**Expected output**:
```
 * Running on http://127.0.0.1:5000
```

Backend is now ready at `http://localhost:5000`

## Frontend Setup (5 minutes)

### Step 1: Install Node Dependencies

```bash
cd frontend
npm install
```

This takes ~2 minutes depending on internet speed.

### Step 2: Verify Environment

Check `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

(Already configured, update only if backend is on different URL)

### Step 3: Start Development Server

```bash
npm run dev
```

**Expected output**:
```
▲ Next.js 14.0.0
  - Local:        http://localhost:3000
```

Frontend is now ready at `http://localhost:3000`

## Complete System Test

### Step 1: Open Application

Navigate to http://localhost:3000 in your browser

### Step 2: Upload a Test PDF

You should see the upload zone. Drag-and-drop a medical policy PDF or use the file picker.

### Step 3: Verify Classification

After upload, the document should be classified as:
- **Single Drug Policy** (green badge) - policy for one drug
- **Multi-Drug Formulary** (purple badge) - policy covering multiple drugs

### Step 4: Test Extraction

1. Enter a drug name (e.g., "Ozempic" or "Metformin")
2. Click "Extract Structured Data"
3. Results should display in organized cards

### Step 5: Test View Toggle

Click "Raw JSON" to see the extracted data in JSON format. Click "Formatted" to return to card view.

## Troubleshooting

### "Connection refused" Error

**Problem**: Frontend can't reach backend

**Solutions**:
- Verify backend is running on port 5000: `lsof -i :5000`
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- Restart both services

### "API key invalid" Error

**Problem**: Google Gemini API key is wrong or missing

**Solutions**:
- Get correct key from: https://ai.google.dev/
- Verify `key.env` is in `AI_Parser/` directory
- Verify `GEMINI_API_KEY` is set correctly
- Restart backend after changing key

### "File upload failed" Error

**Problem**: PDF upload rejected

**Solutions**:
- Ensure file is actual PDF (not renamed document)
- Verify file size < 50MB
- Ensure backend has write permissions to `AI_Parser/uploads/`

### "Extraction failed" Error

**Problem**: AI extraction didn't complete

**Solutions**:
- Check backend logs for full error
- Ensure PDF contains policy text (not scanned images)
- Try a different PDF
- Check Google Gemini API quota

### Port Already in Use

**Problem**: Port 3000 or 5000 already occupied

**Backend (port 5000)**:
```bash
# Find process using port
lsof -i :5000

# Kill process (macOS/Linux)
kill -9 <PID>

# Or use different port in app.py:
# app.run(port=5001)
```

**Frontend (port 3000)**:
```bash
# Find process using port
lsof -i :3000

# Kill process (macOS/Linux)
kill -9 <PID>

# Or use different port
npm run dev -- -p 3001
```

## File Locations

### Backend Files

```
AI_Parser/
├── app.py              ← REST API server
├── key.env             ← Google API key (keep secret)
├── requirements.txt    ← Python dependencies
├── parser.py           ← Extraction logic
├── classification.py   ← Document classification
├── prompt.txt          ← AI extraction schema
└── uploads/            ← Uploaded PDFs (created automatically)
```

### Frontend Files

```
frontend/
├── package.json        ← Dependencies
├── .env.local          ← Environment config
├── pages/
│   ├── _app.tsx        ← App wrapper
│   ├── _document.tsx   ← HTML template
│   └── index.tsx       ← Main page
├── components/         ← React components
│   ├── UploadZone.tsx
│   ├── ClassificationBadge.tsx
│   ├── DrugInput.tsx
│   ├── ResultsDisplay.tsx
│   ├── JsonViewer.tsx
│   └── SkeletonLoader.tsx
├── lib/
│   └── api.ts          ← API client
└── styles/
    └── globals.css     ← Tailwind styles
```

## Common Commands

### Run Both Services (Recommended)

```bash
# Start backend, frontend, and open the browser automatically
bash run.sh
# Press Ctrl+C to stop both
```

### Backend

```bash
# Start server
python app.py

# Check if running
lsof -i :5000

# Stop server
Ctrl+C
```

### Frontend

```bash
# Development server
npm run dev

# Production build
npm run build

# Run production server
npm start

# Lint code
npm run lint
```

## Performance Notes

- **First extraction**: May take 30-60 seconds (AI processing)
- **Subsequent uploads**: Faster as models are cached
- **Large PDFs**: May take longer if >30 pages of policy text

## Security Notes

- **API Keys**: Never commit `key.env` to version control
- **File Uploads**: Validate file types (only PDF accepted)
- **Uploaded Files**: Stored in `uploads/` directory (not in version control)
- **CORS**: Backend allows all origins (suitable for development; restrict for production)

## Next Steps

1. **Load test PDFs**: Try with real medical policy documents
2. **Customize extraction**: Edit `prompt.txt` to adjust extraction rules
3. **Deploy**: See README.md for Vercel/Docker deployment options
4. **Integrate**: Embed frontend into larger application

## Support Resources

- **Next.js Docs**: https://nextjs.org/docs
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Google Gemini API**: https://ai.google.dev/docs
- **Flask Documentation**: https://flask.palletsprojects.com

## Development Workflow

### Making Changes

**Backend API Changes**:
```bash
# Edit app.py
# Server auto-reloads (Flask debug mode)
# No restart needed
```

**Frontend Changes**:
```bash
# Edit components or pages
# Frontend auto-reloads (Next.js dev mode)
# No restart needed
```

### Testing Changes

1. Modify code
2. Changes auto-reload
3. Test in browser
4. Check console for errors

## Production Deployment

### Minimal Setup (Single Machine)

```bash
# Terminal 1: Backend
cd AI_Parser
python app.py

# Terminal 2: Frontend
cd frontend
npm run build && npm start
```

### Docker Deployment

See `frontend/README.md` for Docker setup instructions.

### Cloud Deployment

- **Frontend**: Vercel, Netlify, AWS Amplify
- **Backend**: Heroku, AWS Lambda, Google Cloud Run

---

**You're all set!** Open http://localhost:3000 and start extracting medical policy data.
