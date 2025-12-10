# Getting Started with Resume Explorer

Welcome to Resume Explorer! This guide will walk you through installing, configuring, and using the application to transform your resume into an interactive knowledge graph.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [Your First Session](#your-first-session)
6. [Uploading a Resume](#uploading-a-resume)
7. [Exploring the Graph](#exploring-the-graph)
8. [Understanding Entities](#understanding-entities)
9. [Exporting Your Graph](#exporting-your-graph)
10. [Troubleshooting](#troubleshooting)
11. [Next Steps](#next-steps)

---

## Prerequisites

Before you begin, make sure you have the following installed:

### Required Software

- **Python 3.10 or higher**
  ```bash
  python --version  # Should show 3.10+
  ```

- **Node.js 18 or higher**
  ```bash
  node --version   # Should show 18+
  npm --version    # Should be included with Node.js
  ```

### LLM Provider API Key

You'll need an API key from **one** of these providers:

- **Claude (Anthropic)** - Recommended for best extraction quality
  - Sign up at https://console.anthropic.com/
  - Get your API key from Account Settings

- **OpenAI** - Excellent reliability
  - Sign up at https://platform.openai.com/
  - Get your API key from API Keys section

- **Ollama (Local)** - Free, privacy-first option
  - Install from https://ollama.ai/
  - Pull a model: `ollama pull llama3.1:8b`

---

## Installation

### Step 1: Clone the Repository

```bash
git clone <repo-url>
cd resume_explorer
```

### Step 2: Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

You should see `(venv)` in your terminal prompt, indicating the virtual environment is active.

### Step 3: Frontend Setup

Open a **new terminal window** (keep the backend terminal open) and run:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

---

## Configuration

### Step 1: Create Environment File

In the `backend` directory, create a `.env` file:

```bash
cd backend
cp .env.example .env
```

### Step 2: Configure Your LLM Provider

Edit `backend/.env` and add your API key:

**Option A: Using Claude (Recommended)**
```bash
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-your-key-here
```

**Option B: Using OpenAI**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
```

**Option C: Using Ollama (Local)**
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.1:8b
```

### Step 3: Optional Settings

You can customize these settings in `.env`:

```bash
# Enable experimental DSPy extraction (advanced reasoning)
ENABLE_DSPY=true

# Session limits
SESSION_AUTO_SAVE=true
SESSION_MAX_DOCUMENTS=10

# Default RDF export format
DEFAULT_RDF_FORMAT=turtle  # turtle | rdfxml | jsonld
```

---

## Running the Application

You'll need **two terminal windows** running simultaneously.

### Terminal 1: Start the Backend

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python -m resume_explorer.api.app
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Restarting with stat
```

The backend is now running at **http://localhost:5000**

### Terminal 2: Start the Frontend

```bash
cd frontend
npm run dev
```

You should see:
```
  VITE v5.0.0  ready in 500 ms

  ➜  Local:   http://localhost:3000/
```

The frontend is now running at **http://localhost:3000**

### Open the Application

Open your web browser and navigate to:

```
http://localhost:3000
```

You should see the Resume Explorer welcome screen.

---

## Your First Session

Sessions are containers that hold one or more resumes and their extracted knowledge graphs.

### Step 1: Create a Session

1. Click the **"+ New Session"** button in the sidebar
2. Enter a session name (e.g., "My Resume 2025")
3. Click **"Create"**

Your new session will appear in the session list and be automatically selected.

### Step 2: Session Overview

The session panel shows:
- **Session name** - Click to switch between sessions
- **Document count** - Number of resumes uploaded
- **Created date** - When the session was created
- **Delete button** - Remove the session (careful!)

---

## Uploading a Resume

### Step 1: Prepare Your Resume

Resume Explorer supports:
- **PDF** (.pdf) - Most common format
- **Word** (.doc, .docx)
- **Text** (.txt)
- **Markdown** (.md)

Make sure your resume includes:
- Your name and contact information
- Work experience with job titles, companies, dates
- Skills (technical and soft skills)
- Education history
- Certifications (if applicable)

### Step 2: Upload the File

**Method 1: Drag and Drop**
1. Drag your resume file from your file browser
2. Drop it onto the upload area

**Method 2: Click to Browse**
1. Click the upload area
2. Select your resume file from the file picker

### Step 3: Watch the Extraction

Once uploaded, you'll see real-time progress:

1. **Upload Progress** (0-100%)
   - File is being uploaded to the server

2. **Extraction Started**
   - LLM is analyzing your resume

3. **Extraction Progress**
   - Shows which entities are being extracted:
     - Person (your details)
     - Jobs (work experience)
     - Skills (technical and soft skills)
     - Education (degrees and courses)
     - Certifications
     - Organizations (companies and schools)

4. **Extraction Complete**
   - Graph is ready to explore!

**Extraction typically takes 30-90 seconds** depending on resume length and LLM provider.

---

## Exploring the Graph

Once extraction is complete, you'll see an interactive network graph visualization.

### Understanding the Graph

**Nodes (Circles)**
Each colored circle represents an entity:

- **Red** - Person (you!)
- **Teal** - Jobs/Positions
- **Blue** - Skills
- **Green** - Education
- **Yellow** - Certifications
- **Purple** - Organizations

**Edges (Arrows)**
Lines connecting nodes represent relationships:

- Person → Job: "worked in this position"
- Job → Skill: "used this skill in this job"
- Job → Organization: "worked at this company"
- Person → Education: "completed this education"
- Education → Organization: "studied at this institution"

### Interacting with the Graph

**Zoom and Pan**
- **Scroll wheel** - Zoom in/out
- **Click and drag** on empty space - Pan the view
- **Navigation buttons** (bottom right) - Reset view, zoom controls

**Select Nodes**
- **Click a node** - View detailed information in the right panel
- **Hover over a node** - See a tooltip with the entity label

**Graph Physics**
- The graph uses a physics simulation for layout
- Nodes will settle into an optimal arrangement
- You can drag nodes to rearrange them manually

### Legend

The legend (top right) shows:
- Entity types and their colors
- Count of each entity type
- Total nodes and edges in the graph

---

## Understanding Entities

When you click a node, the **Entity Details Panel** shows comprehensive information.

### Person Entity

Your personal information:
- **Name** - Your full name
- **Email** - Contact email
- **Phone** - Phone number
- **Location** - City, state, country
- **Summary** - Professional summary/bio
- **Relationships** - Links to jobs, skills, education

### Job Entity

Work experience details:
- **Title** - Job title (e.g., "Senior Data Scientist")
- **Organization** - Company name
- **Dates** - Start and end dates (or "Present")
- **Duration** - Calculated length of employment
- **Location** - Office location
- **Description** - Responsibilities and achievements
- **Skills Used** - Technologies and competencies used in this role

### Skill Entity

Skills and competencies:
- **Label** - Skill name (e.g., "Python", "Machine Learning")
- **Category** - Technical, Domain, or Soft Skill
- **Proficiency** - Expert, Advanced, Intermediate, Beginner
- **Years of Experience** - Time using this skill
- **ESCO URI** - Link to European Skills Taxonomy (when available)
- **Related Skills** - SKOS relationships (broader/narrower/related)

### Education Entity

Academic credentials:
- **Degree** - Degree type (e.g., "Bachelor of Science")
- **Field of Study** - Major or specialization
- **Institution** - University/college name
- **Dates** - Start and end dates
- **GPA** - Grade point average (if provided)
- **Honors** - Awards or distinctions

### Certification Entity

Professional certifications:
- **Name** - Certification title
- **Issuer** - Certifying organization
- **Issue Date** - When earned
- **Expiration Date** - When it expires (if applicable)
- **Credential ID** - Verification number
- **Credential URL** - Link to verify certificate

### Organization Entity

Companies and institutions:
- **Name** - Organization name
- **Type** - Company, Educational Institution, Non-Profit, etc.
- **Industry** - Business sector
- **Location** - Headquarters or campus location
- **Website** - Official URL

---

## Exporting Your Graph

You can export your knowledge graph in standard semantic web formats.

### Export Formats

**1. Turtle (.ttl)** - Human-readable RDF
- Easy to read and edit
- Standard format for RDF
- Best for: Developers, semantic web applications

**2. RDF/XML (.rdf)** - XML-based RDF
- Standard XML format
- Widely supported
- Best for: Enterprise systems, XML tools

**3. JSON-LD (.jsonld)** - Web-friendly JSON
- JSON format with linked data
- Easy to parse in JavaScript
- Best for: Web applications, APIs

### How to Export

1. Click the **Export** button in the top toolbar
2. Select your desired format (Turtle, RDF/XML, or JSON-LD)
3. The file will download automatically

### What's in the Export?

The RDF export includes:

- **All entities** with SKOS properties
- **All relationships** between entities
- **SKOS hierarchies** (broader/narrower/related concepts)
- **External vocabulary links** (ESCO skills, schema.org types)
- **Metadata** (creation dates, confidence scores, source documents)

### Example: Turtle Output

```turtle
@prefix re: <http://resumeexplorer.org/ontology#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix schema: <http://schema.org/> .

<http://resumeexplorer.org/resource/person-123>
    a schema:Person ;
    skos:prefLabel "Jane Smith" ;
    re:email "jane@example.com" ;
    re:hasSkill <http://resumeexplorer.org/resource/skill-456> ;
    re:workedAt <http://resumeexplorer.org/resource/job-789> .

<http://resumeexplorer.org/resource/skill-456>
    a re:Skill ;
    skos:prefLabel "Python" ;
    skos:broader <http://resumeexplorer.org/resource/skill-programming> ;
    skos:exactMatch <http://data.europa.eu/esco/skill/python> .
```

---

## Troubleshooting

### Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'resume_explorer'`

**Solution**: Make sure you're in the `backend` directory and the virtual environment is activated:
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

**Error**: `anthropic.AuthenticationError: Invalid API key`

**Solution**: Check your `.env` file:
1. Make sure `CLAUDE_API_KEY` is set correctly
2. Verify the key starts with `sk-ant-`
3. No quotes around the key value
4. Restart the backend after changing `.env`

---

### Frontend Won't Start

**Error**: `EADDRINUSE: address already in use`

**Solution**: Port 3000 is already in use. Either:
- Stop the other application using port 3000
- Or change the port in `vite.config.js`:
```javascript
export default defineConfig({
  server: {
    port: 3001  // Use a different port
  }
})
```

---

**Error**: `Failed to fetch sessions`

**Solution**: Backend is not running or CORS is blocking requests:
1. Make sure backend is running on http://localhost:5000
2. Check backend terminal for errors
3. Try restarting both backend and frontend

---

### Upload Issues

**Error**: Upload gets stuck at 0%

**Solution**:
1. Check file size (max 16MB by default)
2. Verify file format (PDF, DOCX, TXT, MD only)
3. Check backend terminal for error messages
4. Try a different file to isolate the issue

---

**Error**: Extraction fails with "LLM Error"

**Solution**:
1. Verify your API key is valid and has credits
2. Check your internet connection
3. For Ollama: Make sure Ollama is running (`ollama serve`)
4. Check backend logs for detailed error messages

---

### Graph Not Displaying

**Error**: "No graph data available"

**Solution**:
1. Wait for extraction to complete (check progress indicator)
2. Refresh the browser page
3. Check browser console (F12) for JavaScript errors
4. Try re-uploading the document

---

**Error**: Graph is empty but extraction succeeded

**Solution**:
1. The resume might not have recognizable entities
2. Check Entity Panel to see if entities were extracted
3. Try a more structured resume with clear sections
4. Check backend logs for extraction warnings

---

### Common Issues

**Q: Extraction is taking a very long time**

A: This is normal for:
- Large resumes (10+ pages)
- First-time DSPy initialization
- Slow LLM providers

If it takes more than 5 minutes, check backend logs for errors.

---

**Q: Skills are not being linked to ESCO**

A: ESCO linking is best-effort and may not match all skills. Custom or niche skills won't have ESCO URIs. This is expected behavior.

---

**Q: Dates are parsed incorrectly**

A: LLM extraction may misinterpret ambiguous dates. Best practices:
- Use ISO format (YYYY-MM-DD) in your resume
- Spell out months (January 2023 vs 01/2023)
- Be explicit about "Present" for current positions

---

**Q: Can I upload multiple resumes to one session?**

A: Yes! Sessions support multiple documents. Just upload additional files to the same session. The graph will combine all entities.

---

## Next Steps

Congratulations! You've successfully:
- Installed and configured Resume Explorer
- Created your first session
- Uploaded and extracted a resume
- Explored the knowledge graph
- Exported RDF data

### Advanced Topics

**Explore the API**
- Read the [API Documentation](API.md) to integrate with other tools
- Build custom clients using the REST API
- Listen to WebSocket events for real-time updates

**Learn About SKOS**
- Read the [SKOS Schema Documentation](SKOS_SCHEMA.md)
- Understand semantic relationships (broader/narrower/related)
- Explore ESCO skill taxonomy integration

**Customize Extraction**
- Enable DSPy for advanced reasoning (`ENABLE_DSPY=true` in `.env`)
- Experiment with different LLM providers
- Adjust extraction prompts in `resume_extractor.py`

**Contribute**
- Report bugs or request features on GitHub
- Submit pull requests with improvements
- Share your use cases and feedback

### Example Use Cases

**Compare Career Paths**
- Upload resumes of people in your target role
- Identify common skills and career progressions
- Plan your own skill development

**Track Skill Evolution**
- Upload your resume from different years
- See how your skills have grown over time
- Identify gaps and opportunities

**Build a Team Skills Matrix**
- Upload resumes of all team members
- Export combined graph showing team capabilities
- Identify knowledge gaps and training needs

**Research Job Requirements**
- Upload job descriptions as "resumes"
- Extract required skills and qualifications
- Compare against your own resume graph

---

## Getting Help

**Documentation**
- [README.md](../README.md) - Project overview and features
- [API.md](API.md) - Complete API reference
- [SKOS_SCHEMA.md](SKOS_SCHEMA.md) - Vocabulary specification

**Support**
- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and share ideas

**Community**
- Share your knowledge graphs
- Contribute to documentation
- Help other users get started

---

**Happy graph building!** 🎨📊

*Last updated: December 10, 2025*
