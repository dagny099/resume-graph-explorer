# Testing Extraction Method Switching

## Overview
You can now choose between SimplifiedExtractor and DSPy per-upload using a query parameter.

## Default Behavior
- **Default:** SimplifiedExtractor (ENABLE_DSPY=false in .env)
- **Fast:** 1 API call, lower cost
- **Reliable:** Simple JSON parsing

## How to Test

### Method 1: Use SimplifiedExtractor (Default)
Upload normally through the UI at http://localhost:5002

**Expected logs:**
```
INFO - Using simplified extraction pipeline
INFO - Starting simplified extraction (non-DSPy)
```

### Method 2: Use DSPy (Override via API)
Add `?use_dspy=true` to the upload request.

#### Using curl:
```bash
# Get session ID from UI or create one
curl -X POST http://localhost:5002/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Session"}'

# Upload with DSPy
curl -X POST "http://localhost:5002/api/sessions/SESSION_ID/documents?use_dspy=true" \
  -F "file=@/Users/bhs/Downloads/BHS-LinkedIn-Resume.pdf"
```

#### Using browser DevTools:
1. Open DevTools Network tab
2. Upload a document
3. Find the upload request
4. Copy as cURL
5. Add `?use_dspy=true` before the closing quote
6. Run in terminal

**Expected logs with DSPy:**
```
INFO - Created DSPy extraction pipeline (will configure lazily in worker thread)
INFO - DSPy configured lazily in worker thread
INFO - Starting DSPy resume extraction
```

### Method 3: Compare Both Methods
Upload the same resume twice:
1. First upload: Default (SimplifiedExtractor)
2. Second upload: Add `?use_dspy=true`

Compare the extracted entities to see differences in:
- Skill hierarchies (broader/narrower concepts)
- Reasoning field (DSPy only)
- ESCO URIs (DSPy only)

## What Changed

### 1. Threading Bug Fixed ✓
- DSPy now configures in worker thread (lazy initialization)
- No more "settings can only be changed by thread" error

### 2. API Parameter Added ✓
- `?use_dspy=true` - Force DSPy
- `?use_dspy=false` - Force SimplifiedExtractor
- No parameter - Use .env default

### 3. SimplifiedExtractor is Default ✓
- ENABLE_DSPY=false in .env
- Fast, reliable extraction out of the box
- DSPy available when you need it

## Expected Results

### SimplifiedExtractor Output:
```json
{
  "person": {...},
  "jobs": [...],
  "skills": [
    {
      "label": "Python",
      "category": "Technical",
      "proficiency_level": "Expert"
      // No broader_concepts, narrower_concepts, skos_uri
    }
  ],
  "reasoning": ""  // Empty
}
```

### DSPy Output:
```json
{
  "person": {...},
  "jobs": [...],
  "skills": [
    {
      "label": "Python",
      "category": "Technical",
      "proficiency_level": "Expert",
      "broader_concepts": ["Programming Languages"],
      "narrower_concepts": ["Django", "Flask"],
      "related_concepts": ["JavaScript", "Ruby"],
      "skos_uri": "http://data.europa.eu/esco/skill/..."
    }
  ],
  "reasoning": "Extracted 5 skills from resume. Python appears in 3 job descriptions..."
}
```

## Troubleshooting

### If SimplifiedExtractor doesn't work:
- Check logs for JSON parsing errors
- Verify CLAUDE_API_KEY is set
- Check max_tokens (should be 4096+)

### If DSPy doesn't work:
- Check logs for "DSPy configured lazily" message
- Verify threading fix applied
- Check for adapter fallback warnings

## Next Steps

1. **Test now:** Upload your resume with default settings
2. **Compare later:** Upload with `?use_dspy=true` when ready to experiment
3. **Use Ollama:** Set LLM_PROVIDER=ollama for free DSPy extraction
4. **Optimize:** Tune DSPy prompts once you understand the patterns
