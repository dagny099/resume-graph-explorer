# Resume Explorer - End-to-End System Test Plan

## Executive Summary

This plan provides a comprehensive, manual testing approach for the Resume Explorer application with multi-provider LLM comparison (Claude, OpenAI, Ollama) and HTML dashboard reporting. Designed for execution without prior testing experience.

**Estimated Execution Time**: 10-12 hours (1-2 work days)
**Test Coverage**: 87+ test cases across 7 categories
**Output**: HTML dashboard with charts, metrics, and executive summary

---

## Quick Start

### Prerequisites
- Resume Explorer running (backend on :5000, frontend on :3000)
- API keys configured for Claude, OpenAI, and Ollama running locally
- 3-5 sample resumes ready (including `ATLASSIAN RESUME - BARBARA HIDALGO-SOTELO.md`)

### Execution Steps
1. **Day 1 Morning**: Environment setup + Smoke tests + API tests + Claude extraction
2. **Day 1 Afternoon**: OpenAI extraction + Ollama extraction
3. **Day 2 Morning**: Multi-provider comparison + Visualization tests
4. **Day 2 Afternoon**: Edge cases + Performance + Generate HTML dashboard

---

## Test Plan Organization

### Category A: Environment Setup and Smoke Tests (30 min)
**Purpose**: Verify all components are running and providers are accessible

**Test Cases**:
- TC-A-001: Backend health check (HTTP 200 on /health)
- TC-A-002: Frontend accessibility (React app loads on :3000)
- TC-A-003: WebSocket connection (Check DevTools Network > WS)
- TC-A-004: Claude provider availability (CLAUDE_API_KEY valid)
- TC-A-005: OpenAI provider availability (OPENAI_API_KEY valid)
- TC-A-006: Ollama provider availability (`ollama serve` running, llama3.1:8b pulled)

**Success Criteria**: All 6 tests pass before proceeding

---

### Category B: Core API Functionality (45 min)
**Purpose**: Test REST API endpoints (provider-agnostic)

**Test Cases**:
- TC-B-001: Create session (`POST /api/sessions`)
- TC-B-002: List sessions (`GET /api/sessions`)
- TC-B-003: Get session details (`GET /api/sessions/{id}`)
- TC-B-004: Upload document (drag-drop in UI, watch WebSocket events)
- TC-B-005: Get session graph (`GET /api/sessions/{id}/graph`)
- TC-B-006: Export RDF (Turtle) (`GET /api/sessions/{id}/export/turtle`)
- TC-B-007: Export RDF (RDF/XML) (`GET /api/sessions/{id}/export/rdfxml`)
- TC-B-008: Export RDF (JSON-LD) (`GET /api/sessions/{id}/export/jsonld`)
- TC-B-009: Get session statistics (`GET /api/sessions/{id}/stats`)
- TC-B-010: Update session name (`PUT /api/sessions/{id}`)
- TC-B-011: Delete session (`DELETE /api/sessions/{id}`)

**Success Criteria**: ≥10/11 tests pass

---

### Category C: LLM Extraction Pipeline (90 min per provider)
**Purpose**: Test entity extraction for each provider

**Test Cases (run for EACH provider)**:
- TC-C-001: Extract person entity (verify name, email)
- TC-C-002: Extract job entities (count jobs, verify titles)
- TC-C-003: Extract skill entities (count skills, verify key skills)
- TC-C-004: Extract education entities (verify degrees)
- TC-C-005: Extract certification entities (verify certs)
- TC-C-006: Extract organization entities (verify companies)
- TC-C-007: Verify job-organization relationships (check linkage)
- TC-C-008: Verify person-skill relationships (check IDs)
- TC-C-009: Date parsing validation (ISO format dates)
- TC-C-010: Extraction time measurement (record seconds)

**Success Criteria**: ≥8/10 tests pass per provider

---

### Category D: Multi-Provider Comparison (2-5 hours)
**Purpose**: Compare extraction quality across Claude, OpenAI, Ollama

**Strategy**: Use **same resume** (Atlassian - Barbara) for all 3 providers

**Test Cases**:
- TC-D-001: Provider setup validation (all 3 ready)
- TC-D-002: Baseline extraction - Claude (record all metrics)
- TC-D-003: Baseline extraction - OpenAI (record all metrics)
- TC-D-004: Baseline extraction - Ollama (record all metrics)
- TC-D-005: Compare total entity counts (sum all entities)
- TC-D-006: Compare job extraction accuracy (vs. ground truth)
- TC-D-007: Compare skill extraction accuracy (% recall)
- TC-D-008: Compare extraction speed (rank by time)
- TC-D-009: Compare confidence scores (avg confidence)
- TC-D-010: Compare relationship accuracy (manual validation)

**Metrics to Record**:
| Provider | Extraction Time | Total Entities | Jobs | Skills | Avg Confidence | Accuracy % |
|----------|-----------------|----------------|------|--------|----------------|------------|
| Claude   | ___ sec         | ___            | ___  | ___    | ___            | ___        |
| OpenAI   | ___ sec         | ___            | ___  | ___    | ___            | ___        |
| Ollama   | ___ sec         | ___            | ___  | ___    | ___            | ___        |

**Success Criteria**: All 3 providers complete extraction, data collected for comparison

---

### Category E: Graph Visualization (30 min)
**Purpose**: Test Vis.js graph rendering and interaction

**Test Cases**:
- TC-E-001: Graph rendering (verify nodes appear)
- TC-E-002: Node color coding (Person=blue, Job=green, Skill=orange, etc.)
- TC-E-003: Interactive node click (EntityPanel appears)
- TC-E-004: Interactive hover tooltips (tooltip shows label)
- TC-E-005: Graph physics (drag nodes, verify physics)
- TC-E-006: Legend accuracy (counts match nodes)

**Success Criteria**: All 6 tests pass

---

### Category F: Edge Cases and Error Handling (60 min)
**Purpose**: Test error scenarios and boundary conditions

**Test Cases**:
- TC-F-001: Unsupported file type (.jpg → HTTP 400)
- TC-F-002: Large file (>5MB → completes or timeout)
- TC-F-003: Malformed document (random text → low entity count)
- TC-F-004: Session document limit (11th upload → HTTP 400)
- TC-F-005: Concurrent extractions (2 simultaneous uploads)
- TC-F-006: Backend crash recovery (kill mid-extraction, restart)
- TC-F-007: WebSocket disconnection (network disconnect/reconnect)
- TC-F-008: Invalid API key (Claude → clear error message)
- TC-F-009: Ollama service down (stop Ollama → error message)
- TC-F-010: Empty resume (whitespace only → minimal entities)

**Success Criteria**: ≥8/10 tests pass with graceful error handling

---

### Category G: Performance and Scalability (45 min)
**Purpose**: Benchmark extraction times and graph rendering

**Test Cases**:
- TC-G-001: Extraction time benchmark - simple resume (all providers)
- TC-G-002: Extraction time benchmark - complex resume (all providers)
- TC-G-003: Graph rendering performance (50+ nodes < 5s)
- TC-G-004: Memory usage monitoring (5 sequential uploads, check leaks)

**Benchmarks**:
| Provider | Simple Resume | Complex Resume |
|----------|---------------|----------------|
| Claude   | <30s          | <90s           |
| OpenAI   | <30s          | <90s           |
| Ollama   | <60s          | <180s          |

**Success Criteria**: All benchmarks met

---

## Multi-Provider Testing Strategy

### Fair Comparison Criteria

**Controlled Variables**:
- Same resume file (`ATLASSIAN RESUME - BARBARA HIDALGO-SOTELO.md`)
- Same network conditions (no other processes consuming bandwidth)
- Same hardware (dedicated testing session)
- Same DSPy mode (enable for Claude/OpenAI, disable for Ollama)

**Measured Metrics**:
1. **Accuracy**: % of correctly extracted entities (manual verification against resume)
2. **Completeness**: Total entity count vs. expected
3. **Speed**: Extraction time from upload to complete (seconds)
4. **Confidence**: Average confidence scores across all entities
5. **Relationships**: Correct entity linkages (Job→Org, Person→Skill)

### Expected Patterns

Based on typical LLM behavior:
- **Claude**: Highest accuracy and entity count, moderate speed, highest confidence
- **OpenAI**: Fastest extraction, high accuracy, good confidence
- **Ollama**: Slowest extraction, lower accuracy, lower confidence, but free

### Provider Configuration

Before testing each provider, update `.env`:

**For Claude**:
```bash
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-your-key
ENABLE_DSPY=true
```

**For OpenAI**:
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
ENABLE_DSPY=true
```

**For Ollama**:
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.1:8b
ENABLE_DSPY=false
```

**IMPORTANT**: Restart backend after each .env change!

---

## Test Data Strategy

### Resume Test Set (3-5 Resumes)

**Resume 1: Simple Baseline**
- File: `simple_resume.txt` (create manually if needed)
- Entities: 1 person, 2 jobs, 5 skills, 1 education
- Purpose: Smoke test, basic extraction validation
- Test with: All 3 providers

**Resume 2: Moderate - Primary Comparison**
- File: `ATLASSIAN RESUME - BARBARA HIDALGO-SOTELO.md`
- Entities: 1 person, 4-6 jobs, 20-30 skills, 1-2 education, 4-6 orgs
- Purpose: Standard extraction, relationship validation, **PRIMARY MULTI-PROVIDER COMPARISON**
- Test with: All 3 providers (most important test)

**Resume 3: Complex Stress Test**
- File: `complex_resume.pdf` (create if needed)
- Entities: 10+ jobs, 50+ skills, multiple date formats
- Purpose: Stress test, date parsing edge cases
- Test with: Claude and OpenAI (skip Ollama to save time)

**Resume 4: Edge Case - Minimal**
- File: `minimal_resume.txt`
- Entities: Name only, no jobs
- Purpose: Error handling, graceful degradation
- Test with: All 3 providers

**Resume 5: Edge Case - Large** (optional)
- File: `large_resume.pdf` (5-10 MB)
- Entities: 20+ jobs, 100+ skills
- Purpose: Performance, timeout handling
- Test with: Claude only

### Expected Results for Resume 2 (Atlassian - Barbara)

**Ground Truth** (manual count from resume):
- Person: 1 (Barbara Hidalgo-Sotelo)
- Jobs: 5 (estimate - varies by resume version)
- Skills: 25+ (Product Management, Agile, Jira, Confluence, etc.)
- Education: 2 (degree + certifications if listed)
- Organizations: 5+ (Atlassian, universities, prior employers)

**Quality Thresholds**:
- Confidence scores: >0.8 for core entities
- Relationship accuracy: >90%
- Date parsing: 100% (all dates in ISO format or null)

---

## Metrics Collection Framework

### Data Collection Template

Create a file `test_results.json` with this structure:

```json
{
  "test_execution": {
    "test_id": "TEST-2025-12-10-001",
    "tester_name": "Your Name",
    "start_time": "2025-12-10T10:00:00Z",
    "end_time": "2025-12-10T16:30:00Z",
    "environment": {
      "backend_version": "1.0.0",
      "frontend_version": "1.0.0",
      "python_version": "3.10.x",
      "node_version": "18.x"
    }
  },
  "test_cases": [
    {
      "test_id": "TC-A-001",
      "category": "Smoke Tests",
      "name": "Backend Health Check",
      "provider": "N/A",
      "status": "PASS",
      "execution_time_sec": 2,
      "notes": "HTTP 200 OK, health endpoint responding",
      "timestamp": "2025-12-10T10:05:00Z"
    }
  ],
  "provider_metrics": [
    {
      "provider": "claude",
      "model": "claude-sonnet-4-20250514",
      "resume_filename": "ATLASSIAN RESUME - BARBARA HIDALGO-SOTELO.md",
      "extraction_time_sec": 45.3,
      "entities_extracted": {
        "person": 1,
        "jobs": 5,
        "skills": 23,
        "education": 2,
        "certifications": 1,
        "organizations": 5
      },
      "avg_confidence": 0.92,
      "accuracy_percent": 95,
      "relationship_accuracy": 100,
      "notes": "Excellent structure, all dates parsed correctly"
    }
  ],
  "errors": [
    {
      "test_id": "TC-F-008",
      "error_type": "AuthenticationError",
      "message": "Invalid Claude API key",
      "severity": "HIGH",
      "workaround": "Verified key in .env, restarted backend"
    }
  ]
}
```

### Manual Data Collection Checklist

For **each test case**, record:
- [ ] Test ID (e.g., TC-A-001)
- [ ] Pass/Fail/Skip status
- [ ] Execution time (seconds)
- [ ] Expected vs. actual results
- [ ] Screenshot (if failure)
- [ ] Notes/observations

For **provider comparisons**, record:
- [ ] Provider name and model
- [ ] Resume filename
- [ ] Extraction time (start to complete)
- [ ] Entity counts by type (person, jobs, skills, education, certs, orgs)
- [ ] Average confidence score
- [ ] Manual accuracy assessment (% correct entities)
- [ ] Notable differences or issues

---

## HTML Dashboard Specification

### Dashboard Layout

**Section 1: Executive Summary** (Top Card)
```
┌─────────────────────────────────────────────────────────┐
│  RESUME EXPLORER - END-TO-END TEST RESULTS             │
│  Test Date: 2025-12-10  |  Tester: [Your Name]         │
├─────────────────────────────────────────────────────────┤
│  Overall Status: ✅ PASS (95%)                          │
│  Total Tests: 87  |  Passed: 83  |  Failed: 4          │
│  Duration: 6h 30m  |  Providers Tested: 3              │
└─────────────────────────────────────────────────────────┘
```

**Section 2: Visual Charts** (2x2 Grid)

1. **Test Results Pie Chart** - Pass/Fail/Skip distribution
2. **Provider Comparison Bar Chart** - Total entities by provider
3. **Extraction Time Bar Chart** - Speed comparison
4. **Accuracy Radar Chart** - Multi-metric comparison (Person, Jobs, Skills, Relationships, Confidence)

**Section 3: Test Category Summary Table**

| Category | Total Tests | Passed | Failed | Pass Rate | Avg Time |
|----------|-------------|--------|--------|-----------|----------|
| Environment Setup | 6 | 6 | 0 | 100% | 30 min |
| Core API | 11 | 10 | 1 | 91% | 45 min |
| Extraction (All) | 30 | 28 | 2 | 93% | 4.5 hrs |
| Multi-Provider | 10 | 10 | 0 | 100% | 2 hrs |
| Visualization | 6 | 6 | 0 | 100% | 30 min |
| Edge Cases | 10 | 9 | 1 | 90% | 60 min |
| Performance | 4 | 4 | 0 | 100% | 45 min |

**Section 4: Provider Comparison Matrix Table**

| Metric | Claude Sonnet | OpenAI GPT-4o | Ollama Llama3.1 | Winner |
|--------|---------------|---------------|-----------------|--------|
| Extraction Speed | 45.3s | 38.2s | 127.5s | OpenAI ⭐ |
| Total Entities | 37 | 35 | 28 | Claude ⭐ |
| Jobs Extracted | 5 | 5 | 4 | Tie |
| Skills Extracted | 23 | 22 | 17 | Claude ⭐ |
| Avg Confidence | 0.92 | 0.88 | 0.71 | Claude ⭐ |
| Accuracy % | 95% | 92% | 78% | Claude ⭐ |
| Relationship Accuracy | 100% | 95% | 85% | Claude ⭐ |
| Cost per Extract | $0.15 | $0.12 | $0.00 | Ollama ⭐ |

**Section 5: Detailed Test Results Table** (Expandable)

| Test ID | Category | Name | Provider | Status | Time | Notes |
|---------|----------|------|----------|--------|------|-------|
| TC-A-001 | Smoke | Backend Health | N/A | ✅ PASS | 2s | HTTP 200 OK |
| TC-C-012 | Extraction | Extract Jobs | Claude | ✅ PASS | 45s | 5 jobs found |
| TC-D-005 | Multi-Provider | Compare Skills | All | ⚠️ PARTIAL | 180s | Ollama missing 6 skills |

### Dashboard Generation Options

**Option 1: Python Script (Recommended)**

Use the provided script `generate_dashboard.py`:

```bash
# After collecting all test data in test_results.json
python generate_dashboard.py test_results.json

# Output: test_report.html
# Open in browser
open test_report.html  # macOS
```

**Option 2: Manual HTML Creation**

Copy the HTML template provided in the implementation section and fill in values manually.

### Dashboard Technology Stack

- **HTML5** - Single file output
- **Bootstrap 5 CDN** - Professional styling
- **Chart.js CDN** - Interactive charts
- **Embedded JSON** - Test data in `<script>` tag
- **No build tools required** - Open directly in browser

---

## Implementation Files

### Critical Files for Testing

1. **backend/resume_explorer/api/routes.py**
   - Contains all REST API endpoints to test
   - Lines 50-300: Session CRUD, document upload, graph retrieval, RDF export

2. **backend/resume_explorer/services/llm_client.py**
   - LLM provider abstraction
   - Lines 20-150: Provider switching logic, availability checks

3. **backend/resume_explorer/services/resume_extractor.py**
   - Core extraction logic
   - Lines 100-400: Entity extraction, date parsing, confidence scoring

4. **backend/resume_explorer/api/websocket.py**
   - WebSocket event emitter
   - Lines 30-120: Extraction events (started, progress, complete, error)

5. **ATLASSIAN RESUME - BARBARA HIDALGO-SOTELO.md**
   - Primary test resume for multi-provider comparison
   - Ground truth for accuracy validation

### Files to Create

1. **test_results.json** - Manual test data collection file
2. **generate_dashboard.py** - Dashboard generation script (provided in plan)
3. **test_report.html** - Generated HTML dashboard (output)
4. **simple_resume.txt** - Baseline test resume (if not exists)
5. **test_execution_checklist.md** - Day-by-day execution tracker

---

## Execution Timeline

### Recommended 2-Day Schedule

**Day 1: Setup + Provider Testing (6 hours)**

| Time | Activity | Duration |
|------|----------|----------|
| 9:00-9:30 | Pre-test setup (verify all providers configured) | 30 min |
| 9:30-10:00 | Category A: Smoke tests (all 6 tests) | 30 min |
| 10:00-10:45 | Category B: Core API (11 tests) | 45 min |
| 10:45-11:00 | Break | 15 min |
| 11:00-12:30 | Category C: Claude extraction (10 tests) | 90 min |
| 12:30-13:30 | Lunch | 60 min |
| 13:30-15:00 | Category C: OpenAI extraction (10 tests) | 90 min |
| 15:00-15:15 | Break | 15 min |
| 15:15-16:45 | Category C: Ollama extraction (10 tests) | 90 min |
| 16:45-17:00 | Day 1 review, backup test_results.json | 15 min |

**Day 2: Comparison + Reporting (6 hours)**

| Time | Activity | Duration |
|------|----------|----------|
| 9:00-11:00 | Category D: Multi-provider comparison (10 tests) | 120 min |
| 11:00-11:30 | Category E: Visualization (6 tests) | 30 min |
| 11:30-12:30 | Lunch | 60 min |
| 12:30-13:30 | Category F: Edge cases (10 tests) | 60 min |
| 13:30-14:15 | Category G: Performance (4 tests) | 45 min |
| 14:15-15:15 | Data analysis, accuracy calculations | 60 min |
| 15:15-16:00 | Generate HTML dashboard | 45 min |
| 16:00-16:30 | Review dashboard, add final notes | 30 min |

**Total Time: 12 hours** (2 full work days)

---

## Detailed Test Case Examples

### Example: TC-D-002 - Baseline Extraction - Claude

**Provider**: Claude
**Resume**: `ATLASSIAN RESUME - BARBARA HIDALGO-SOTELO.md`

**Prerequisites**:
- Backend running with `LLM_PROVIDER=claude` in .env
- Frontend running on :3000
- CLAUDE_API_KEY is valid

**Steps**:
1. Open frontend in browser: `http://localhost:3000`
2. Click "✨ New Session" button
3. Enter session name: "Multi-Provider Test - Claude"
4. Click "Create"
5. Drag `ATLASSIAN RESUME - BARBARA HIDALGO-SOTELO.md` to upload area
6. **Start timer** when upload begins
7. Watch WebSocket events in browser DevTools Console:
   - `extraction_started` event
   - `extraction_progress` events (multiple)
   - `entity_extracted` events (one per entity)
   - `extraction_complete` event
8. **Stop timer** when `extraction_complete` fires
9. Open browser DevTools > Network tab
10. Find request to `/api/sessions/{id}/graph`
11. Copy response JSON to clipboard
12. Count entities in JSON:
    - `nodes` array, filter by `group: "Person"` → count
    - `nodes` array, filter by `group: "Job"` → count
    - `nodes` array, filter by `group: "Skill"` → count
    - Repeat for Education, Certification, Organization
13. Calculate average confidence:
    - For each node, find `metadata.confidence`
    - Sum all confidence values
    - Divide by total node count
14. Record extraction time from timer

**Expected Results**:
- Extraction time: 30-60 seconds
- Person entities: 1
- Job entities: 4-6
- Skill entities: 20-30
- Education entities: 1-2
- Certification entities: 0-2
- Organization entities: 4-6
- Average confidence: >0.85

**Record in test_results.json**:
```json
{
  "provider": "claude",
  "model": "claude-sonnet-4-20250514",
  "resume_filename": "ATLASSIAN RESUME - BARBARA HIDALGO-SOTELO.md",
  "extraction_time_sec": 45.3,
  "entities_extracted": {
    "person": 1,
    "jobs": 5,
    "skills": 23,
    "education": 2,
    "certifications": 1,
    "organizations": 5
  },
  "avg_confidence": 0.92,
  "accuracy_percent": 95,
  "notes": "All core entities extracted, dates parsed correctly"
}
```

**Status**: PASS if extraction completes and entity counts are reasonable

---

### Example: TC-F-001 - Unsupported File Type

**Provider**: Any (N/A for this test)

**Prerequisites**:
- Backend and frontend running
- Session created

**Steps**:
1. Create a `.jpg` image file (can be empty or any image)
2. Try uploading `.jpg` file to session
3. Observe error message in UI
4. Check browser DevTools > Console for error details
5. Verify backend logs show rejection message

**Expected Results**:
- Upload fails immediately (before reaching backend)
- Error message displayed: "Unsupported file type. Please upload PDF, DOCX, TXT, or MD files."
- No extraction triggered
- Session document count unchanged

**Screenshot**: Capture error message in UI

**Status**: PASS if error is gracefully handled with clear message

---

## Troubleshooting Guide

### Common Issues

**Issue 1: Backend won't start - "CLAUDE_API_KEY not set"**
- **Solution**:
  1. Verify `.env` file exists in `/Users/bhs/PROJECTS/resume_explorer/backend/`
  2. Check `CLAUDE_API_KEY=sk-ant-...` is set (no quotes)
  3. Restart backend: `python -m resume_explorer.api.app`

**Issue 2: Ollama extraction timeout after 60s**
- **Solution**:
  1. Check Ollama is running: `curl http://localhost:11434/api/tags`
  2. Verify model downloaded: `ollama list` (should show llama3.1:8b)
  3. Increase timeout in `llm_client.py` if needed
  4. Try smaller model: `ollama pull llama3.1:7b`

**Issue 3: WebSocket events not appearing in frontend**
- **Solution**:
  1. Open DevTools > Network > WS tab
  2. Verify WebSocket connection shows "101 Switching Protocols"
  3. Check backend logs for "Client connected to extraction stream"
  4. Hard refresh browser: Ctrl+Shift+R (Cmd+Shift+R on macOS)
  5. Restart both backend and frontend

**Issue 4: Graph not rendering after extraction**
- **Solution**:
  1. Verify document status is "complete": `curl http://localhost:5000/api/sessions/{id}`
  2. Check graph endpoint returns data: `curl http://localhost:5000/api/sessions/{id}/graph`
  3. Look for JavaScript errors in browser console
  4. Clear browser cache and reload

**Issue 5: Provider comparison shows very different results**
- **Solution**:
  1. Verify using exact same resume file for all 3 providers
  2. Check provider-specific settings (DSPy on/off)
  3. Review extraction logs for errors or warnings
  4. Re-run test to check consistency (LLMs can vary)
  5. Consider differences expected (Ollama is smaller model)

**Issue 6: RDF export fails with serialization error**
- **Solution**:
  1. Verify session has at least 1 completed document
  2. Check backend logs for specific RDF error message
  3. Try different format (turtle → jsonld)
  4. Check if any entities have invalid URIs

---

## Success Criteria

### Overall Test Execution
- **Pass Rate**: ≥90% of all test cases pass
- **Provider Coverage**: All 3 providers tested successfully (Claude, OpenAI, Ollama)
- **Dashboard Delivery**: HTML dashboard generated with all 4 charts and 5 sections
- **Documentation**: All failures documented with screenshots and notes in test_results.json

### Multi-Provider Comparison
- **Claude**: Highest entity count and confidence scores (expected)
- **OpenAI**: Fastest extraction time with high accuracy (expected)
- **Ollama**: Completes extraction with reasonable entity count (expected to be lower)
- **Consistency**: All 3 providers extract core entities (person, jobs, skills)
- **Data Quality**: All providers achieve >70% accuracy for core entities

### Dashboard Quality
- **Executive Summary**: Clear overall status (PASS/FAIL) with key metrics
- **Charts**: All 4 charts render correctly (pie, bar, bar, radar)
- **Tables**: Complete data for all test cases and provider comparisons
- **Professional**: Suitable for presentation to executives or stakeholders
- **Actionable**: Failures clearly documented with notes and recommendations

### Testing Process Quality
- **Reproducible**: Test execution documented clearly enough to repeat
- **Traceable**: All test results linked to test cases
- **Complete**: All 7 categories executed
- **Timely**: Execution completed within 2 work days

---

## Dashboard Generation Script

### Python Script: `generate_dashboard.py`

Save this script in the project root:

```python
#!/usr/bin/env python3
"""
Resume Explorer - Test Dashboard Generator
Generates HTML dashboard from test results JSON
Usage: python generate_dashboard.py test_results.json
"""

import json
import sys
import os
from datetime import datetime

def generate_dashboard(test_data):
    """Generate HTML dashboard from test data"""

    # Calculate summary stats
    total_tests = len(test_data['test_cases'])
    passed = sum(1 for tc in test_data['test_cases'] if tc['status'] == 'PASS')
    failed = sum(1 for tc in test_data['test_cases'] if tc['status'] == 'FAIL')
    skipped = sum(1 for tc in test_data['test_cases'] if tc['status'] == 'SKIP')
    pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0

    # Provider metrics
    providers = test_data.get('provider_metrics', [])

    # Generate provider comparison rows
    provider_rows = ""
    if providers:
        provider_headers = "".join([f"<th>{p['provider'].title()}</th>" for p in providers])
        provider_rows = f"""
            <tr>
                <td><strong>Extraction Time</strong></td>
                {"".join([f"<td>{p['extraction_time_sec']:.1f}s</td>" for p in providers])}
            </tr>
            <tr>
                <td><strong>Total Entities</strong></td>
                {"".join([f"<td>{sum(p['entities_extracted'].values())}</td>" for p in providers])}
            </tr>
            <tr>
                <td><strong>Jobs Extracted</strong></td>
                {"".join([f"<td>{p['entities_extracted'].get('jobs', 0)}</td>" for p in providers])}
            </tr>
            <tr>
                <td><strong>Skills Extracted</strong></td>
                {"".join([f"<td>{p['entities_extracted'].get('skills', 0)}</td>" for p in providers])}
            </tr>
            <tr>
                <td><strong>Avg Confidence</strong></td>
                {"".join([f"<td>{p['avg_confidence']:.2f}</td>" for p in providers])}
            </tr>
            <tr>
                <td><strong>Accuracy %</strong></td>
                {"".join([f"<td>{p.get('accuracy_percent', 'N/A')}%</td>" for p in providers])}
            </tr>
        """

    # Generate test result rows
    test_rows = ""
    for tc in test_data['test_cases']:
        status_class = f"status-{tc['status'].lower()}"
        test_rows += f"""
            <tr>
                <td>{tc['test_id']}</td>
                <td>{tc['category']}</td>
                <td>{tc['name']}</td>
                <td class="{status_class}">{tc['status']}</td>
                <td>{tc.get('execution_time_sec', 'N/A')}s</td>
                <td>{tc.get('notes', '')[:100]}</td>
            </tr>
        """

    # Prepare provider data for Chart.js
    provider_data = json.dumps([{
        'provider': p['provider'],
        'total': sum(p['entities_extracted'].values()),
        'jobs': p['entities_extracted'].get('jobs', 0),
        'skills': p['entities_extracted'].get('skills', 0),
        'time': p['extraction_time_sec']
    } for p in providers])

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Explorer - E2E Test Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        .status-pass {{ color: #28a745; font-weight: bold; }}
        .status-fail {{ color: #dc3545; font-weight: bold; }}
        .status-skip {{ color: #6c757d; font-weight: bold; }}
        .metric-card {{ border-left: 4px solid #007bff; }}
        .chart-container {{ position: relative; height: 300px; margin: 20px 0; }}
        .provider-winner {{ background-color: #d4edda; }}
    </style>
</head>
<body>
<div class="container my-5">
    <!-- Section 1: Executive Summary -->
    <div class="card metric-card mb-4">
        <div class="card-body">
            <h1 class="card-title">📊 Resume Explorer - End-to-End Test Report</h1>
            <p class="text-muted">
                Test Date: {test_data['test_execution']['start_time'][:10]} |
                Tester: {test_data['test_execution'].get('tester_name', 'N/A')} |
                Duration: {test_data['test_execution'].get('end_time', 'N/A')[:10]}
            </p>
            <hr>
            <div class="row text-center">
                <div class="col-md-3">
                    <h2 class="{"status-pass" if pass_rate >= 90 else "status-fail"}">{pass_rate:.1f}%</h2>
                    <p class="text-muted">Pass Rate</p>
                </div>
                <div class="col-md-3">
                    <h2>{total_tests}</h2>
                    <p class="text-muted">Total Tests</p>
                </div>
                <div class="col-md-3">
                    <h2 class="status-pass">{passed}</h2>
                    <p class="text-muted">Passed</p>
                </div>
                <div class="col-md-3">
                    <h2 class="{"status-fail" if failed > 0 else "text-muted"}">{failed}</h2>
                    <p class="text-muted">Failed</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Section 2: Visual Charts -->
    <div class="row mb-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>Test Results by Status</h5>
                    <div class="chart-container">
                        <canvas id="statusPieChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>Provider Comparison - Total Entities</h5>
                    <div class="chart-container">
                        <canvas id="providerBarChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="row mb-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>Extraction Time Comparison</h5>
                    <div class="chart-container">
                        <canvas id="timeBarChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>Provider Accuracy Radar</h5>
                    <div class="chart-container">
                        <canvas id="accuracyRadarChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Section 3: Provider Comparison Table -->
    {"<div class='card mb-4'><div class='card-body'><h5>🔬 Multi-Provider Comparison Matrix</h5><table class='table table-bordered'><thead><tr><th>Metric</th>" + provider_headers + "</tr></thead><tbody>" + provider_rows + "</tbody></table></div></div>" if providers else ""}

    <!-- Section 4: Detailed Test Results -->
    <div class="card mb-4">
        <div class="card-body">
            <h5>📋 Detailed Test Results</h5>
            <div class="table-responsive">
                <table class="table table-sm table-striped">
                    <thead>
                        <tr>
                            <th>Test ID</th>
                            <th>Category</th>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Time</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {test_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="text-center text-muted mt-5 mb-3">
        <p>Generated by Resume Explorer Test Dashboard Generator</p>
        <p>Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</div>

<script>
// Test data
const providerData = {provider_data};

// Chart 1: Status Pie Chart
const statusCtx = document.getElementById('statusPieChart').getContext('2d');
new Chart(statusCtx, {{
    type: 'pie',
    data: {{
        labels: ['Passed', 'Failed', 'Skipped'],
        datasets: [{{
            data: [{passed}, {failed}, {skipped}],
            backgroundColor: ['#28a745', '#dc3545', '#6c757d']
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ position: 'bottom' }}
        }}
    }}
}});

// Chart 2: Provider Entity Bar Chart
if (providerData.length > 0) {{
    const providerCtx = document.getElementById('providerBarChart').getContext('2d');
    new Chart(providerCtx, {{
        type: 'bar',
        data: {{
            labels: providerData.map(p => p.provider.charAt(0).toUpperCase() + p.provider.slice(1)),
            datasets: [
                {{
                    label: 'Jobs',
                    data: providerData.map(p => p.jobs),
                    backgroundColor: '#28a745'
                }},
                {{
                    label: 'Skills',
                    data: providerData.map(p => p.skills),
                    backgroundColor: '#ffc107'
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'bottom' }}
            }},
            scales: {{
                y: {{ beginAtZero: true }}
            }}
        }}
    }});

    // Chart 3: Extraction Time Bar Chart
    const timeCtx = document.getElementById('timeBarChart').getContext('2d');
    new Chart(timeCtx, {{
        type: 'bar',
        data: {{
            labels: providerData.map(p => p.provider.charAt(0).toUpperCase() + p.provider.slice(1)),
            datasets: [{{
                label: 'Extraction Time (seconds)',
                data: providerData.map(p => p.time),
                backgroundColor: '#007bff'
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }}
            }},
            scales: {{
                y: {{ beginAtZero: true }}
            }}
        }}
    }});

    // Chart 4: Accuracy Radar (placeholder with sample data)
    const radarCtx = document.getElementById('accuracyRadarChart').getContext('2d');
    new Chart(radarCtx, {{
        type: 'radar',
        data: {{
            labels: ['Person', 'Jobs', 'Skills', 'Education', 'Relationships'],
            datasets: providerData.map((p, i) => ({{
                label: p.provider.charAt(0).toUpperCase() + p.provider.slice(1),
                data: [95, 90, 85, 88, 92], // Placeholder - replace with actual accuracy data
                backgroundColor: ['rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(255, 206, 86, 0.2)'][i],
                borderColor: ['rgb(255, 99, 132)', 'rgb(54, 162, 235)', 'rgb(255, 206, 86)'][i],
                borderWidth: 2
            }}))
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                r: {{
                    beginAtZero: true,
                    max: 100
                }}
            }},
            plugins: {{
                legend: {{ position: 'bottom' }}
            }}
        }}
    }});
}}
</script>
</body>
</html>
"""
    return html

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_dashboard.py test_results.json")
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)

    with open(input_file, 'r') as f:
        test_data = json.load(f)

    html = generate_dashboard(test_data)

    output_file = "test_report.html"
    with open(output_file, 'w') as f:
        f.write(html)

    abs_path = os.path.abspath(output_file)
    print(f"✅ Dashboard generated: {output_file}")
    print(f"📊 Open in browser: file://{abs_path}")
```

**Make executable**:
```bash
chmod +x generate_dashboard.py
```

---

## Next Steps After Plan Approval

1. **Create test_results.json template** - Copy JSON structure from Section "Metrics Collection Framework"
2. **Verify all 3 LLM providers** - Run TC-A-004, TC-A-005, TC-A-006
3. **Day 1 execution** - Environment setup through Ollama extraction
4. **Day 2 execution** - Multi-provider comparison through dashboard generation
5. **Review and share dashboard** - Present test_report.html to stakeholders

---

## Key Takeaways

- **Manual testing approach** - No automation required, follow step-by-step checklists
- **Fair multi-provider comparison** - Same resume, controlled conditions, comprehensive metrics
- **Executive-ready reporting** - HTML dashboard with charts suitable for presentations
- **Comprehensive coverage** - 87+ test cases across 7 categories
- **Realistic timeline** - 10-12 hours over 2 work days
- **Actionable results** - Clear pass/fail criteria with troubleshooting guidance

---

*End of Test Plan*
