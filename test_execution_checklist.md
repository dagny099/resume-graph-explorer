# Resume Explorer - Test Execution Checklist

**Tester**: _______________ | **Start Date**: _______________

## Pre-Test Setup (30 minutes)

### Environment Verification
- [ ] Backend running on http://localhost:5000
- [ ] Frontend running on http://localhost:3000
- [ ] Browser DevTools open (F12)
- [ ] Terminal window for backend logs
- [ ] Terminal window for frontend logs
- [ ] Text editor with `test_results.json` open

### Provider Configuration
- [ ] Claude: API key set in `.env`, `LLM_PROVIDER=claude`, `ENABLE_DSPY=true`
- [ ] OpenAI: API key set in `.env` (for later testing)
- [ ] Ollama: Service running (`ollama serve`), llama3.1:8b pulled

### Test Data Prepared
- [ ] `ATLASSIAN RESUME - BARBARA HIDALGO-SOTELO.md` accessible
- [ ] `simple_resume.txt` created and accessible
- [ ] Additional 1-3 resumes ready (optional)

---

## Day 1 Morning (9:00 AM - 12:30 PM)

### Category A: Smoke Tests (9:00-9:30 AM)

- [ ] TC-A-001: Backend health check
  - Command: `curl http://localhost:5000/health`
  - Expected: HTTP 200, JSON response
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-A-002: Frontend accessibility
  - URL: http://localhost:3000
  - Expected: React app loads
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-A-003: WebSocket connection
  - Check: DevTools > Network > WS tab
  - Expected: Connection established
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-A-004: Claude provider availability
  - Check: Backend starts without errors
  - Expected: "ClaudeBackend initialized" in logs
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-A-005: OpenAI provider availability (verify later)
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-A-006: Ollama provider availability
  - Command: `curl http://localhost:11434/api/tags`
  - Expected: llama3.1:8b in list
  - Status: ___ | Time: ___ | Notes: ___

**Smoke Tests Complete**: ___ PASS / ___ FAIL | Continue? YES / NO

---

### Category B: Core API Tests (9:30-10:45 AM)

- [ ] TC-B-001: Create session
  - Method: POST /api/sessions with name "Test Session 1"
  - Session ID: _______________
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-B-002: List sessions
  - Method: GET /api/sessions
  - Sessions found: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-B-003: Get session details
  - Method: GET /api/sessions/{id}
  - Document count: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-B-004: Upload document (simple_resume.txt)
  - Upload via UI drag-and-drop
  - Document ID: _______________
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-B-005: Get session graph
  - Method: GET /api/sessions/{id}/graph
  - Node count: ___ | Edge count: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-B-006: Export RDF (Turtle)
  - Method: GET /api/sessions/{id}/export/turtle
  - File size: ___ KB
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-B-007: Export RDF (RDF/XML)
  - Method: GET /api/sessions/{id}/export/rdfxml
  - File size: ___ KB
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-B-008: Export RDF (JSON-LD)
  - Method: GET /api/sessions/{id}/export/jsonld
  - File size: ___ KB
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-B-009: Get session statistics
  - Method: GET /api/sessions/{id}/stats
  - Total entities: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-B-010: Update session name
  - New name: "Test Session 1 - Updated"
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-B-011: Delete session (create temp session first)
  - Temp session ID: _______________
  - Status: ___ | Time: ___ | Notes: ___

**Core API Tests Complete**: ___ PASS / ___ FAIL

**BREAK**: 10:45-11:00 AM (15 minutes)

---

### Category C: Claude Extraction (11:00 AM - 12:30 PM)

**Configuration**: `LLM_PROVIDER=claude`, `ENABLE_DSPY=true`, backend restarted

**Session Name**: "Claude Extraction Test"
**Session ID**: _______________

- [ ] TC-C-001: Extract person entity (simple_resume.txt)
  - Person name found: _______________
  - Email found: _______________
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-002: Extract job entities (ATLASSIAN RESUME)
  - Jobs found: ___ (expected: 4-6)
  - Job titles: _______________
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-003: Extract skill entities (ATLASSIAN RESUME)
  - Skills found: ___ (expected: 20-30)
  - Sample skills: _______________
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-004: Extract education entities
  - Education records: ___ (expected: 1-2)
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-005: Extract certification entities
  - Certifications: ___ (expected: 0-2)
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-006: Extract organization entities
  - Organizations: ___ (expected: 4-6)
  - Organization names: _______________
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-007: Verify job-organization relationships
  - Total job→org links: ___
  - Relationship accuracy: ___% (manual check)
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-008: Verify person-skill relationships
  - Total person→skill links: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-009: Date parsing validation
  - Dates in ISO format: ___ / ___
  - Date parsing success rate: ___%
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-010: Extraction time measurement
  - **Start time**: ___:___
  - **End time**: ___:___
  - **Duration**: ___ seconds (expected: <60s)
  - Status: ___ | Time: ___ | Notes: ___

**Claude Extraction Complete**: ___ PASS / ___ FAIL

**Record Claude Metrics in test_results.json:**
```json
{
  "provider": "claude",
  "extraction_time_sec": ___,
  "entities_extracted": {
    "person": ___,
    "jobs": ___,
    "skills": ___,
    "education": ___,
    "certifications": ___,
    "organizations": ___
  },
  "avg_confidence": ___,
  "accuracy_percent": ___,
  "notes": "___"
}
```

**LUNCH**: 12:30-1:30 PM (60 minutes)

---

## Day 1 Afternoon (1:30 PM - 5:00 PM)

### Category C: OpenAI Extraction (1:30-3:00 PM)

**Configuration**: Change `.env` to `LLM_PROVIDER=openai`, `ENABLE_DSPY=true`, **RESTART BACKEND**

**Session Name**: "OpenAI Extraction Test"
**Session ID**: _______________

- [ ] TC-C-001: Extract person entity
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-002: Extract job entities (ATLASSIAN RESUME)
  - Jobs found: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-003: Extract skill entities
  - Skills found: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-004: Extract education
  - Education records: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-005: Extract certifications
  - Certifications: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-006: Extract organizations
  - Organizations: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-007: Job-organization relationships
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-008: Person-skill relationships
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-009: Date parsing
  - Date parsing success: ___%
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-010: Extraction time
  - **Duration**: ___ seconds
  - Status: ___ | Time: ___ | Notes: ___

**OpenAI Extraction Complete**: ___ PASS / ___ FAIL

**Record OpenAI Metrics in test_results.json**

**BREAK**: 3:00-3:15 PM (15 minutes)

---

### Category C: Ollama Extraction (3:15-4:45 PM)

**Configuration**: Change `.env` to `LLM_PROVIDER=ollama`, `ENABLE_DSPY=false`, **RESTART BACKEND**

**Session Name**: "Ollama Extraction Test"
**Session ID**: _______________

- [ ] TC-C-001: Extract person entity
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-002: Extract job entities (ATLASSIAN RESUME)
  - Jobs found: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-003: Extract skill entities
  - Skills found: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-004: Extract education
  - Education records: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-005: Extract certifications
  - Certifications: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-006: Extract organizations
  - Organizations: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-007: Job-organization relationships
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-008: Person-skill relationships
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-009: Date parsing
  - Date parsing success: ___%
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-C-010: Extraction time
  - **Duration**: ___ seconds (may be >60s for Ollama)
  - Status: ___ | Time: ___ | Notes: ___

**Ollama Extraction Complete**: ___ PASS / ___ FAIL

**Record Ollama Metrics in test_results.json**

---

### Day 1 Wrap-Up (4:45-5:00 PM)

- [ ] Backup `test_results.json` to safe location
- [ ] Review all data collected today
- [ ] Note any issues for tomorrow
- [ ] Prepare for Day 2 multi-provider comparison

**Day 1 Summary**:
- Total tests run: ___
- Total passed: ___
- Total failed: ___
- Issues to investigate: ___

---

## Day 2 Morning (9:00 AM - 12:30 PM)

### Category D: Multi-Provider Comparison (9:00-11:00 AM)

**Goal**: Direct comparison of same resume (ATLASSIAN) across all 3 providers

- [ ] TC-D-001: Verify all 3 provider sessions exist
  - Claude session: ___ ✓
  - OpenAI session: ___ ✓
  - Ollama session: ___ ✓
  - Status: ___ | Notes: ___

- [ ] TC-D-002: Compare total entity counts
  | Provider | Total Entities |
  |----------|----------------|
  | Claude   | ___            |
  | OpenAI   | ___            |
  | Ollama   | ___            |

  - Winner: _______________
  - Status: ___ | Notes: ___

- [ ] TC-D-003: Compare job extraction
  | Provider | Jobs Found |
  |----------|------------|
  | Claude   | ___        |
  | OpenAI   | ___        |
  | Ollama   | ___        |

  - Ground truth (manual count): ___
  - Most accurate: _______________
  - Status: ___ | Notes: ___

- [ ] TC-D-004: Compare skill extraction
  | Provider | Skills Found |
  |----------|--------------|
  | Claude   | ___          |
  | OpenAI   | ___          |
  | Ollama   | ___          |

  - Expected key skills found (PM, Agile, Jira, etc.): ___ / ___
  - Status: ___ | Notes: ___

- [ ] TC-D-005: Compare extraction speed
  | Provider | Time (sec) |
  |----------|------------|
  | Claude   | ___        |
  | OpenAI   | ___        |
  | Ollama   | ___        |

  - Fastest: _______________
  - Status: ___ | Notes: ___

- [ ] TC-D-006: Compare confidence scores
  | Provider | Avg Confidence |
  |----------|----------------|
  | Claude   | ___            |
  | OpenAI   | ___            |
  | Ollama   | ___            |

  - Highest confidence: _______________
  - Status: ___ | Notes: ___

- [ ] TC-D-007: Compare accuracy (manual validation)
  - Claude accuracy: ___%
  - OpenAI accuracy: ___%
  - Ollama accuracy: ___%
  - Most accurate: _______________
  - Status: ___ | Notes: ___

- [ ] TC-D-008: Compare relationship accuracy
  - Claude relationships correct: ___ / ___
  - OpenAI relationships correct: ___ / ___
  - Ollama relationships correct: ___ / ___
  - Status: ___ | Notes: ___

- [ ] TC-D-009: Document differences
  - Key differences between providers: _______________
  - Entities unique to Claude: _______________
  - Entities unique to OpenAI: _______________
  - Entities unique to Ollama: _______________
  - Status: ___ | Notes: ___

- [ ] TC-D-010: Determine overall winner
  - Best accuracy: _______________
  - Best speed: _______________
  - Best confidence: _______________
  - Best value (free): Ollama
  - **Recommended provider**: _______________
  - Status: ___ | Notes: ___

**Multi-Provider Comparison Complete**: ___ PASS / ___ FAIL

---

### Category E: Visualization Tests (11:00-11:30 AM)

**Use any provider session with good graph data**

- [ ] TC-E-001: Graph rendering
  - Nodes visible: ___ (should match entity count)
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-E-002: Node color coding
  - Person (blue): ✓ / ✗
  - Job (green): ✓ / ✗
  - Skill (orange): ✓ / ✗
  - Education (purple): ✓ / ✗
  - Certification (red): ✓ / ✗
  - Organization (gray): ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-E-003: Interactive node click
  - EntityPanel appears: ✓ / ✗
  - Entity details correct: ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-E-004: Hover tooltips
  - Tooltips show entity names: ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-E-005: Graph physics
  - Nodes settle into layout: ✓ / ✗
  - Drag node works: ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-E-006: Legend accuracy
  - Legend counts match nodes: ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

**Visualization Tests Complete**: ___ PASS / ___ FAIL

**LUNCH**: 11:30 AM - 12:30 PM (60 minutes)

---

## Day 2 Afternoon (12:30 PM - 4:30 PM)

### Category F: Edge Cases (12:30-1:30 PM)

- [ ] TC-F-001: Unsupported file type (.jpg)
  - Error message displayed: ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-F-002: Large file (>5MB if available)
  - Extraction completes or timeout message: ✓ / ✗
  - Time: ___ seconds
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-F-003: Malformed document (random text)
  - Extraction completes: ✓ / ✗
  - Entity count: ___ (should be low)
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-F-004: Session document limit (SESSION_MAX_DOCUMENTS=10)
  - 11th upload rejected: ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-F-005: Concurrent extractions (2 uploads simultaneously)
  - Both complete successfully: ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-F-006: Backend crash recovery
  - Document status after restart: ___
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-F-007: WebSocket disconnection
  - Extraction continues on backend: ✓ / ✗
  - UI reconnects: ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-F-008: Invalid API key (Claude)
  - Clear error message: ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-F-009: Ollama service down
  - Error message: ✓ / ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-F-010: Empty resume (whitespace only)
  - Extraction completes: ✓ / ✗
  - Entity count: ___ (should be 0 or minimal)
  - Status: ___ | Time: ___ | Notes: ___

**Edge Cases Complete**: ___ PASS / ___ FAIL

---

### Category G: Performance (1:30-2:15 PM)

- [ ] TC-G-001: Simple resume benchmark (all providers)
  | Provider | Time (sec) | Benchmark |
  |----------|------------|-----------|
  | Claude   | ___        | <30s      |
  | OpenAI   | ___        | <30s      |
  | Ollama   | ___        | <60s      |

  - Status: ___ | Notes: ___

- [ ] TC-G-002: Complex resume benchmark (if available)
  | Provider | Time (sec) | Benchmark |
  |----------|------------|-----------|
  | Claude   | ___        | <90s      |
  | OpenAI   | ___        | <90s      |
  | Ollama   | ___        | <180s     |

  - Status: ___ | Notes: ___

- [ ] TC-G-003: Graph rendering performance (50+ nodes)
  - Render time: ___ seconds (expected: <5s)
  - Frame rate: Smooth ✓ / Laggy ✗
  - Status: ___ | Time: ___ | Notes: ___

- [ ] TC-G-004: Memory usage monitoring
  - Memory before: ___ MB
  - Memory after 5 uploads: ___ MB
  - Memory leak detected: YES / NO
  - Status: ___ | Time: ___ | Notes: ___

**Performance Tests Complete**: ___ PASS / ___ FAIL

---

### Data Analysis (2:15-3:15 PM)

- [ ] Calculate overall pass rate: ___ %
- [ ] Count test results by category:
  - Smoke: ___ / 6
  - API: ___ / 11
  - Extraction: ___ / 30
  - Multi-Provider: ___ / 10
  - Visualization: ___ / 6
  - Edge Cases: ___ / 10
  - Performance: ___ / 4

- [ ] Finalize accuracy percentages:
  - Claude: ___%
  - OpenAI: ___%
  - Ollama: ___%

- [ ] Update `test_results.json` with all final metrics

- [ ] Screenshot any interesting graphs or errors

---

### Dashboard Generation (3:15-4:00 PM)

- [ ] Verify `test_results.json` is complete and valid JSON
- [ ] Run dashboard generator:
  ```bash
  python generate_dashboard.py test_results.json
  ```
- [ ] Open `test_report.html` in browser
- [ ] Verify all 4 charts render correctly:
  - [ ] Status pie chart
  - [ ] Provider comparison bar chart
  - [ ] Extraction time bar chart
  - [ ] Accuracy radar chart
- [ ] Verify all tables populated:
  - [ ] Executive summary metrics
  - [ ] Provider comparison matrix
  - [ ] Detailed test results

- [ ] Take screenshot of dashboard for records

---

### Final Review (4:00-4:30 PM)

- [ ] Review dashboard for completeness
- [ ] Add any final notes to test_results.json
- [ ] Create summary of key findings:
  - Best provider overall: _______________
  - Critical bugs found: _______________
  - Recommended improvements: _______________

- [ ] Save all files:
  - [ ] test_results.json
  - [ ] test_report.html
  - [ ] Screenshots (if any)
  - [ ] Test data files

- [ ] Backup all test artifacts

---

## Test Execution Complete!

**Final Metrics**:
- Total tests executed: ___ / 87
- Overall pass rate: ___ %
- Duration: ___ hours
- Recommended LLM provider: _______________

**Dashboard location**: `file:///Users/bhs/PROJECTS/resume_explorer/test_report.html`

**Next Steps**:
- [ ] Share test_report.html with stakeholders
- [ ] File bug reports for any critical failures
- [ ] Document recommended provider configuration
- [ ] Archive test results for future reference
