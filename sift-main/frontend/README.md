# Medical Policy Extraction Frontend

Production-ready Next.js frontend for extracting structured drug policy data from PDF documents.

## Features

- 📄 **Drag-and-drop PDF upload** with validation
- 🏷️ **Automatic document classification** (single-drug vs multi-drug)
- 💬 **Target drug input** for focused extraction
- 📊 **Beautiful structured results display**
- 🔀 **View toggle** between formatted and raw JSON
- 📋 **Copy-to-clipboard** JSON export
- ⚡ **Real-time loading states** and error handling
- 🎨 **Minimalist SaaS design** with Tailwind CSS

## Tech Stack

- **Framework**: Next.js 14
- **Styling**: Tailwind CSS
- **Language**: TypeScript
- **State Management**: React Hooks
- **HTTP Client**: Fetch API

## Prerequisites

- Node.js 16+ and npm/yarn
- Backend API running on `http://localhost:5000`

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create `.env.local` (already provided):

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

Update this if your backend runs on a different URL.

### 3. Start Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:3000`

## Backend Setup

### 1. Install Backend Dependencies

```bash
cd AI_Parser
pip install -r requirements.txt
```

### 2. Set Up Environment

Create `key.env` in `AI_Parser/` directory:

```env
GEMINI_API_KEY=your_api_key_here
```

### 3. Start Backend API

```bash
python app.py
```

The API will run on `http://localhost:5000`

## API Endpoints

### `POST /api/upload`

Upload a PDF file.

**Request**:
```
Content-Type: multipart/form-data
file: <PDF file>
```

**Response**:
```json
{
  "file_id": "filename.pdf",
  "file_path": "/path/to/file.pdf",
  "original_name": "filename.pdf",
  "size": 1024000,
  "pages": 15
}
```

### `POST /api/classify`

Classify a PDF as single_drug or multi_drug.

**Request**:
```json
{
  "file_path": "/path/to/file.pdf"
}
```

**Response**:
```json
{
  "classification": "single_drug",
  "file_path": "/path/to/file.pdf"
}
```

### `POST /api/extract`

Extract structured data from a PDF.

**Request**:
```json
{
  "file_path": "/path/to/file.pdf",
  "target_drug": "Ozempic",
  "drug_keywords": ["semaglutide", "GLP-1"]
}
```

**Response**:
```json
{
  "data": {
    "payer_name": "Cigna",
    "drug_name": {
      "brand": "Ozempic",
      "generic": "semaglutide"
    },
    ...
  },
  "file_path": "/path/to/file.pdf",
  "target_drug": "Ozempic",
  "classification": "single_drug"
}
```

## Project Structure

```
frontend/
├── pages/
│   ├── _app.tsx          # App wrapper
│   ├── _document.tsx     # HTML document
│   └── index.tsx         # Main page
├── components/
│   ├── UploadZone.tsx    # File upload component
│   ├── ClassificationBadge.tsx
│   ├── DrugInput.tsx     # Drug name input
│   ├── ResultsDisplay.tsx  # Structured results
│   ├── JsonViewer.tsx    # JSON display
│   ├── SkeletonLoader.tsx
│   └── index.ts          # Component exports
├── lib/
│   └── api.ts            # API client service
├── styles/
│   └── globals.css       # Global Tailwind styles
├── .env.local            # Environment variables
├── tailwind.config.js    # Tailwind configuration
├── postcss.config.js     # PostCSS configuration
├── next.config.js        # Next.js configuration
└── package.json          # Dependencies
```

## Component Documentation

### UploadZone

Drag-and-drop file upload with visual feedback.

```tsx
<UploadZone
  onFileSelect={(file) => handleUpload(file)}
  disabled={false}
  isLoading={false}
/>
```

### ClassificationBadge

Displays document classification result.

```tsx
<ClassificationBadge
  classification="single_drug"
  isLoading={false}
/>
```

### DrugInput

Text input for target drug name.

```tsx
<DrugInput
  value={drugName}
  onChange={setDrugName}
  error={errorMessage}
/>
```

### ResultsDisplay

Renders structured policy data in organized sections.

```tsx
<ResultsDisplay
  data={extractedData}
  targetDrug="Ozempic"
/>
```

### JsonViewer

Displays JSON with syntax highlighting.

```tsx
<JsonViewer
  data={extractedData}
  onCopy={handleCopy}
  showCopyButton={true}
/>
```

## User Flow

1. **Upload PDF**: Drag-and-drop or click to select a medical policy PDF
2. **Auto-Classification**: Document is automatically classified as single-drug or multi-drug
3. **Enter Drug Name**: Input the target drug you want to extract data for
4. **Extract Data**: Click "Extract Structured Data" button
5. **View Results**: See formatted results or raw JSON
6. **Export**: Copy JSON to clipboard or start over

## Design Details

### Color Scheme

- **Primary**: Blue (Indigo-500 #4f46e5)
- **Success**: Green
- **Warning**: Orange/Yellow
- **Error**: Red
- **Neutral**: Gray/White

### Typography

- **Headings**: Bold, large (28-36px)
- **Body**: Regular weight, 16px
- **Labels**: Medium weight, 14px
- **Code**: Monospace, 14px

### Spacing

- **Padding**: 4px, 8px, 12px, 16px, 24px, 32px
- **Gaps**: 8px, 12px, 16px, 24px
- **Rounded corners**: 8px for buttons, 12px for cards/inputs, 16px for major sections

## Error Handling

- **Upload errors**: Network issues, invalid files, file too large
- **Classification errors**: PDF parsing failures (defaults to single_drug)
- **Extraction errors**: AI service timeouts, malformed responses
- **All errors**: Displayed with clear messages, option to retry

## Performance Optimizations

- Lazy component loading with Next.js
- Optimized re-renders with React.memo (where applicable)
- Efficient API client with error boundaries
- CSS animations use GPU-accelerated transforms

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile browsers: iOS Safari, Chrome Mobile

## Development

### Build for Production

```bash
npm run build
npm start
```

### Lint Code

```bash
npm run lint
```

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Docker

Create `Dockerfile`:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

Build and run:

```bash
docker build -t policy-extraction-frontend .
docker run -p 3000:3000 policy-extraction-frontend
```

## Environment Variables

### Frontend (.env.local)

```env
# Required: Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### Backend (key.env)

```env
# Required: Google Gemini API key
GEMINI_API_KEY=your_key_here
```

## Troubleshooting

### Frontend won't connect to backend

- Check backend is running on correct port (5000)
- Verify `NEXT_PUBLIC_API_URL` matches backend URL
- Check browser console for CORS errors
- Restart both services

### File upload fails

- Ensure file is valid PDF
- Check file size is under 50MB
- Verify backend has write permissions to `uploads/` directory

### Extraction returns errors

- Check GEMINI_API_KEY is valid
- Verify PDF contains relevant policy text
- Check backend logs for detailed errors

## Support

For issues or questions, check the backend repository or review API logs.

## License

MIT
