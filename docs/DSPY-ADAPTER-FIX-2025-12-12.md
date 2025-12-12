# Fix DSPy JSON Adapter for Resume Extraction
**Date**: 2025-12-12
**Status**: Ready for Implementation
**Priority**: High - Blocks DSPy learning goals

---

## Executive Summary

The DSPy pipeline for resume extraction is failing because the adapter expects `[[ ## field ## ]]` delimited format but LLMs (Claude, GPT-4) return JSON. This document provides a phased implementation plan to fix the adapter while preserving the working SimplifiedExtractor fallback.

**Learning Goals Enabled After Fix**:
1. Compare different LLM backends (Claude vs OpenAI vs Ollama)
2. Build RAG/Q&A systems over resume knowledge graphs
3. Use DSPy optimizers (BootstrapFewShot, MIPROv2) for prompt improvement

---

## Background: Current Architecture

### What Works
- **SimplifiedExtractor** (`backend/resume_explorer/services/extraction_dspy.py` lines 133-322)
  - Bypasses DSPy adapters entirely
  - Calls `llm_backend.generate()` directly
  - Uses `json.loads()` to parse response
  - Returns structured dict with person, jobs, skills, education, etc.
  - **This is the fallback when `ENABLE_DSPY=false`**

### What's Broken
- **DSPy Pipeline** with `ResumeExtractionModule`
  - Uses `dspy.Predict(ExtractResumeEntities)` signature
  - Configured with `LenientChatAdapter`
  - LLM returns: `{"person": {...}, "jobs": [...], ...}`
  - ChatAdapter expects: `[[ ## person ## ]]\n{...}\n[[ ## jobs ## ]]\n[...]`
  - Parser fails → fallback puts entire JSON as **string** into first field
  - Later code tries `person.get('name')` → `AttributeError: 'str' object has no attribute 'get'`

### Key Files Overview

```
backend/resume_explorer/services/
├── llm_client.py
│   ├── LLMBackend (abstract base)
│   ├── ClaudeBackend, OpenAIBackend, OllamaBackend
│   ├── DSPyLMAdapter (wraps backends for DSPy)
│   └── LenientChatAdapter (BROKEN - needs replacement)
│
├── extraction_dspy.py
│   ├── ExtractResumeEntities (DSPy Signature - defines 7 output fields)
│   ├── ResumeExtractionModule (DSPy Module - uses dspy.Predict)
│   ├── SimplifiedExtractor (working fallback)
│   └── create_extraction_pipeline() (NEEDS UPDATE - line 345-355)
│
└── resume_extractor.py
    └── ResumeExtractor (main service - calls pipeline)

.env
├── ENABLE_DSPY=true/false (controls which pipeline to use)
└── LLM_PROVIDER=claude/openai/ollama
```

---

## Problem Analysis

### Error Flow
```
1. User uploads resume
   ↓
2. ResumeExtractor calls pipeline.forward(resume_text)
   ↓
3. ResumeExtractionModule.forward() calls dspy.Predict(ExtractResumeEntities)
   ↓
4. DSPy generates prompt asking for [[ ## field ## ]] format
   ↓
5. LLM ignores format, returns JSON: {"person": {...}, "jobs": [...], ...}
   ↓
6. ChatAdapter.parse() looks for [[ ## ]] markers, finds none
   ↓
7. LenientChatAdapter.parse() catches exception, does naive fallback:
      - Takes entire JSON string
      - Assigns to outputs[primary_field] (usually "reasoning")
      - Fills rest with empty defaults
   ↓
8. Returns: {"reasoning": "{...json...}", "person": "", "jobs": [], ...}
   ↓
9. ResumeExtractor._convert_to_entities() tries person.get('name')
   ↓
10. ERROR: AttributeError: 'str' object has no attribute 'get'
```

### Why SimplifiedExtractor Works
- No adapter layer - direct `json.loads()` parsing
- Returns proper dict structure: `{"person": {...}, "jobs": [...]}`
- Type access works: `person.get('name')` ✅

### Why We Need DSPy to Work
DSPy provides powerful features **blocked** by this bug:
- **Optimizers**: BootstrapFewShot, MIPROv2 for automatic prompt improvement
- **Metrics**: Systematic evaluation of extraction quality
- **Backend comparison**: Test Claude vs OpenAI vs Ollama systematically
- **Advanced modules**: ChainOfThought, ReAct for better reasoning
- **RAG foundation**: Building Q&A systems over resume data

---

## Solution: Phased Adapter Fix

### Phase 1: Try DSPy's Built-in JSONAdapter (5 minutes)

DSPy already has a `JSONAdapter` designed for JSON responses. Try it first.

**File**: `backend/resume_explorer/services/extraction_dspy.py`

**Line 345-355** - Change adapter:

```python
# BEFORE:
from .llm_client import DSPyLMAdapter, LenientChatAdapter

dspy_lm = DSPyLMAdapter(backend=llm_backend)

dspy.settings.configure(
    lm=dspy_lm,
    adapter=LenientChatAdapter()
)
logger.info("Using DSPy extraction pipeline with LenientChatAdapter")

# AFTER:
from .llm_client import DSPyLMAdapter
from dspy.adapters import JSONAdapter  # Built-in DSPy adapter

dspy_lm = DSPyLMAdapter(backend=llm_backend)

dspy.settings.configure(
    lm=dspy_lm,
    adapter=JSONAdapter()  # Use built-in JSON adapter
)
logger.info("Using DSPy extraction pipeline with JSONAdapter")
```

**Test Immediately**:
```bash
cd backend
source .venv/bin/activate
export ENABLE_DSPY=true
export LLM_PROVIDER=claude

# Restart backend
lsof -ti :5002 | xargs kill
python -m resume_explorer.api.app

# Upload resume in UI, check logs for:
# - "Using DSPy extraction pipeline with JSONAdapter"
# - No AttributeError
# - Successful extraction
```

**If Phase 1 works**: ✅ Done! Move to testing and DSPy learning.

**If Phase 1 fails**: JSONAdapter might be too strict (requires all fields present). Proceed to Phase 2.

---

### Phase 2: Create Custom JSONChatAdapter (1 hour)

Build a more forgiving adapter that provides defaults for missing fields.

#### Step 2.1: Add JSONChatAdapter Class

**File**: `backend/resume_explorer/services/llm_client.py`

**Location**: After `LenientChatAdapter` class (~line 523)

**Add this class**:

```python
class JSONChatAdapter(ChatAdapter):
    """
    JSON-aware adapter that bridges JSON responses to DSPy signatures.

    More forgiving than built-in JSONAdapter:
    - Provides sensible defaults for missing fields
    - Falls back to delimited format if JSON parsing fails
    - Uses DSPy's parse_value() for type validation

    Design pattern from DSPy's JSONAdapter (dspy/adapters/json_adapter.py)
    but with enhanced error handling for production use.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._warned = False
        logger.info("JSONChatAdapter initialized - handles JSON and delimited formats")

    def parse(self, signature, completion: str) -> Dict[str, Any]:
        """
        Parse LLM response, supporting both JSON and [[ ## field ## ]] formats.

        Flow:
        1. Try to detect/parse as JSON
        2. If JSON valid and has signature fields → map to outputs
        3. Otherwise, fall back to parent ChatAdapter.parse()

        Args:
            signature: DSPy signature with output_fields
            completion: LLM response string

        Returns:
            Dict mapping field names to parsed/typed values

        Raises:
            AdapterParseError: If both parsing strategies fail
        """
        # Step 1: Try JSON parsing
        try:
            parsed_json = self._try_parse_json(completion)
            if parsed_json is not None:
                return self._map_json_to_fields(signature, parsed_json, completion)
        except Exception as e:
            logger.debug(f"JSON parsing failed: {e}")

        # Step 2: Fall back to standard [[ ## field ## ]] parsing
        try:
            return super().parse(signature, completion)
        except Exception as e:
            # Both strategies failed
            logger.error(f"Both JSON and delimited parsing failed")
            raise AdapterParseError(
                adapter_name="JSONChatAdapter",
                signature=signature,
                lm_response=completion,
                message=f"Failed to parse as JSON or delimited format: {e}"
            )

    def _try_parse_json(self, completion: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to extract and parse JSON from completion.

        Uses same approach as DSPy's JSONAdapter:
        - Regex to extract JSON object
        - json_repair.loads() for lenient parsing

        Returns:
            Parsed JSON dict if successful, None otherwise
        """
        import regex
        import json_repair

        # Clean markdown code blocks (```json ... ```)
        cleaned = completion.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Extract JSON object using recursive regex (same as JSONAdapter)
        # Pattern matches nested braces: {outer{inner}outer}
        pattern = r"\{(?:[^{}]|(?R))*\}"
        match = regex.search(pattern, cleaned, regex.DOTALL)

        if match:
            json_str = match.group(0)
            try:
                parsed = json_repair.loads(json_str)
                if isinstance(parsed, dict):
                    logger.debug(f"Successfully parsed JSON with keys: {list(parsed.keys())}")
                    return parsed
            except Exception as e:
                logger.debug(f"json_repair.loads failed: {e}")

        return None

    def _map_json_to_fields(
        self,
        signature,
        parsed_json: Dict[str, Any],
        original_completion: str
    ) -> Dict[str, Any]:
        """
        Map JSON keys to signature output fields with type validation.

        Uses DSPy's parse_value() utility for type coercion and validation.
        Provides sensible defaults for missing fields instead of failing.

        Args:
            signature: DSPy signature with output_fields
            parsed_json: Parsed JSON dict from LLM
            original_completion: Original response (for error messages)

        Returns:
            Dict mapping signature field names to typed values
        """
        from dspy.adapters.utils import parse_value

        output_fields = signature.output_fields
        result = {}

        # Map each signature field
        for field_name, field_info in output_fields.items():
            if field_name in parsed_json:
                # Field present in JSON - validate type
                raw_value = parsed_json[field_name]

                try:
                    # Use DSPy's parse_value for type validation
                    # Handles: str, bool, int, float, list, dict, Literal, Enum
                    # Uses Pydantic TypeAdapter internally
                    typed_value = parse_value(raw_value, field_info.annotation)
                    result[field_name] = typed_value
                    logger.debug(f"Mapped '{field_name}': {type(typed_value).__name__}")
                except Exception as e:
                    logger.warning(f"Type validation failed for '{field_name}': {e}")
                    # Use raw value as fallback (lenient)
                    result[field_name] = raw_value
            else:
                # Field missing in JSON - provide default
                result[field_name] = self._get_default_value(field_info.annotation)

                if not self._warned:
                    logger.warning(
                        f"Field '{field_name}' not in JSON response. "
                        f"Available keys: {list(parsed_json.keys())}. Using default."
                    )
                    self._warned = True

        return result

    def _get_default_value(self, annotation) -> Any:
        """
        Get sensible default value for a field based on its type annotation.

        Args:
            annotation: Type annotation from signature.output_fields[field].annotation

        Returns:
            Default value matching the type (empty list, dict, string, etc.)
        """
        if annotation == str:
            return ""
        elif annotation == bool:
            return False
        elif annotation == int:
            return 0
        elif annotation == float:
            return 0.0
        elif annotation == list or annotation == List:
            return []
        elif annotation == dict or annotation == Dict:
            return {}
        else:
            # For complex types, try to instantiate
            try:
                return annotation()
            except:
                return None
```

#### Step 2.2: Update Exports

**File**: `backend/resume_explorer/services/llm_client.py`

**Line 569** - Add to `__all__`:

```python
__all__ = [
    "LLMClient",
    "LLMBackend",
    "ClaudeBackend",
    "OpenAIBackend",
    "OllamaBackend",
    "DSPyLMAdapter",
    "LenientChatAdapter",  # Keep for backward compatibility
    "JSONChatAdapter",      # NEW - add this
    "DSPY_AVAILABLE",
    "create_llm_client",
]
```

#### Step 2.3: Use Custom Adapter

**File**: `backend/resume_explorer/services/extraction_dspy.py`

**Line 345-355** - Update adapter:

```python
# Replace JSONAdapter with JSONChatAdapter
from .llm_client import DSPyLMAdapter, JSONChatAdapter

dspy_lm = DSPyLMAdapter(backend=llm_backend)

dspy.settings.configure(
    lm=dspy_lm,
    adapter=JSONChatAdapter()  # Custom adapter with defaults
)
logger.info("Using DSPy extraction pipeline with JSONChatAdapter")
```

---

## Testing Strategy

### Test 1: Manual End-to-End Test

```bash
cd backend
source .venv/bin/activate

# Configure for DSPy
export ENABLE_DSPY=true
export LLM_PROVIDER=claude

# Restart backend
lsof -ti :5002 | xargs kill
python -m resume_explorer.api.app

# Check startup logs for:
# - "Using DSPy extraction pipeline with JSONAdapter" (or JSONChatAdapter)
# - "DSPy adapter initialized"

# Upload a resume in the UI
# Check logs for:
# - "Successfully parsed JSON with keys: ['reasoning', 'person', 'jobs'...]"
# - "Converting extracted data to entity objects"
# - NO AttributeError about 'str' object
# - Successful extraction completion

# Verify in UI:
# - Person name, email displayed correctly
# - Jobs list populated
# - Skills shown
# - Organizations linked correctly
```

### Test 2: Backend Comparison (Learning Goal)

```python
# In Python shell or Jupyter notebook:
from resume_explorer.services.llm_client import create_llm_client
from resume_explorer.services.extraction_dspy import create_extraction_pipeline

# Sample resume
resume_text = """
John Doe
john.doe@example.com
Software Engineer at TechCorp (2020-Present)
Skills: Python, Django, PostgreSQL, React
Education: BS Computer Science, MIT
"""

# Test Claude
print("Testing Claude backend...")
claude_backend = create_llm_client('claude').backend
claude_pipeline = create_extraction_pipeline(claude_backend, use_dspy=True)
claude_result = claude_pipeline.forward(resume_text)

print(f"Claude extracted:")
print(f"  Person: {claude_result['person']}")
print(f"  Jobs: {len(claude_result['jobs'])} positions")
print(f"  Skills: {len(claude_result['skills'])} skills")

# Test OpenAI (requires OPENAI_API_KEY in .env)
print("\nTesting OpenAI backend...")
openai_backend = create_llm_client('openai').backend
openai_pipeline = create_extraction_pipeline(openai_backend, use_dspy=True)
openai_result = openai_pipeline.forward(resume_text)

print(f"OpenAI extracted:")
print(f"  Person: {openai_result['person']}")
print(f"  Jobs: {len(openai_result['jobs'])} positions")
print(f"  Skills: {len(openai_result['skills'])} skills")

# Compare results
print("\nComparison:")
print(f"  Jobs: Claude={len(claude_result['jobs'])}, OpenAI={len(openai_result['jobs'])}")
print(f"  Skills: Claude={len(claude_result['skills'])}, OpenAI={len(openai_result['skills'])}")
```

### Test 3: Verify SimplifiedExtractor Fallback

```bash
# Configure for SimplifiedExtractor
export ENABLE_DSPY=false

# Restart backend
lsof -ti :5002 | xargs kill
python -m resume_explorer.api.app

# Check logs for:
# - "Using simplified extraction pipeline"

# Upload resume - should still work
# This verifies we didn't break the fallback
```

### Test 4: Unit Tests

**File**: `backend/tests/test_extraction.py`

**Add new test function**:

```python
def test_json_adapter_parsing():
    """Test JSONAdapter/JSONChatAdapter with mock JSON response."""
    import json
    from resume_explorer.services.llm_client import LLMBackend, LLMClient
    from resume_explorer.services.extraction_dspy import create_extraction_pipeline

    # Mock backend that returns JSON
    class MockLLMBackend(LLMBackend):
        def __init__(self, response):
            super().__init__("mock-model")
            self.response = response

        def generate(self, prompt, **kwargs):
            return self.response

        def is_available(self):
            return True

    # Mock JSON response matching ExtractResumeEntities signature
    mock_json_response = json.dumps({
        "reasoning": "Extracted basic person and job info",
        "person": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "location": "San Francisco, CA",
            "summary": "Software Engineer"
        },
        "jobs": [
            {
                "title": "Software Engineer",
                "organization_id": "org-techcorp",
                "start_date": "2020-01-01",
                "end_date": None,
                "is_current": True,
                "location": "San Francisco, CA",
                "description": "Developed features",
                "skills_used": ["Python", "Django"],
                "technologies_used": ["PostgreSQL", "Redis"],
                "achievements": ["Improved performance"]
            }
        ],
        "skills": [
            {
                "label": "Python",
                "category": "Technical",
                "proficiency_level": "Expert",
                "years_experience": 5.0
            }
        ],
        "education": [],
        "certifications": [],
        "organizations": [
            {
                "id": "org-techcorp",
                "name": "TechCorp",
                "org_type": "Company",
                "location": "San Francisco, CA",
                "website": "https://techcorp.com"
            }
        ]
    })

    # Create pipeline with mock backend
    backend = MockLLMBackend(response=mock_json_response)
    pipeline = create_extraction_pipeline(backend, use_dspy=True)

    # Run extraction
    result = pipeline.forward(resume_text="Test resume text...")

    # Verify structure
    assert 'person' in result
    assert isinstance(result['person'], dict), f"person should be dict, got {type(result['person'])}"
    assert result['person']['name'] == "John Doe"

    assert 'jobs' in result
    assert isinstance(result['jobs'], list), f"jobs should be list, got {type(result['jobs'])}"
    assert len(result['jobs']) == 1
    assert result['jobs'][0]['title'] == "Software Engineer"

    assert 'skills' in result
    assert isinstance(result['skills'], list)

    print("✅ JSONAdapter test passed!")


def test_simplified_extractor_still_works():
    """Verify SimplifiedExtractor fallback not broken."""
    # Same mock setup as above
    mock_json_response = json.dumps({
        "person": {"name": "Test"},
        "jobs": [],
        "skills": [],
        "education": [],
        "certifications": [],
        "organizations": []
    })

    backend = MockLLMBackend(response=mock_json_response)

    # Create pipeline with use_dspy=False
    from resume_explorer.services.extraction_dspy import SimplifiedExtractor
    pipeline = create_extraction_pipeline(backend, use_dspy=False)

    # Should be SimplifiedExtractor instance
    assert isinstance(pipeline, SimplifiedExtractor)

    # Should still work
    result = pipeline.extract("test resume")
    assert 'person' in result
    assert isinstance(result['person'], dict)

    print("✅ SimplifiedExtractor fallback test passed!")
```

Run tests:
```bash
cd backend
pytest tests/test_extraction.py::test_json_adapter_parsing -v
pytest tests/test_extraction.py::test_simplified_extractor_still_works -v
```

---

## Critical Files Reference

### Files to Modify

| File | Lines | Change | Priority |
|------|-------|--------|----------|
| `backend/resume_explorer/services/extraction_dspy.py` | 345-355 | Change adapter config | **Phase 1** |
| `backend/resume_explorer/services/llm_client.py` | ~523 | Add JSONChatAdapter class | **Phase 2** |
| `backend/resume_explorer/services/llm_client.py` | 569 | Update __all__ exports | **Phase 2** |
| `backend/tests/test_extraction.py` | End of file | Add unit tests | **Both** |

### Files to Reference (Read-Only)

| File | Purpose |
|------|---------|
| `backend/.venv/lib/python3.11/site-packages/dspy/adapters/json_adapter.py` | Study JSONAdapter.parse() implementation (lines 153-183) |
| `backend/.venv/lib/python3.11/site-packages/dspy/adapters/utils.py` | Study parse_value() type validation (lines 137-187) |
| `backend/.venv/lib/python3.11/site-packages/dspy/adapters/chat_adapter.py` | Study ChatAdapter.parse() for [[ ## ]] format (lines 169-204) |

---

## Expected Outcomes

### Immediate Results After Fix

- ✅ **No more AttributeError**: `person.get('name')` works
- ✅ **Proper data types**: `person` is dict, `jobs` is list
- ✅ **UI displays correctly**: Name, email, jobs, skills all visible
- ✅ **Logs show success**: "Successfully parsed JSON with keys: [...]"
- ✅ **SimplifiedExtractor unchanged**: Fallback still works with `ENABLE_DSPY=false`

### Learning Goals Unlocked

#### 1. Backend Comparison (Immediate)
```python
# Compare Claude vs OpenAI extraction quality
for provider in ['claude', 'openai']:
    backend = create_llm_client(provider).backend
    pipeline = create_extraction_pipeline(backend, use_dspy=True)
    result = pipeline.forward(resume)
    print(f"{provider}: {len(result['jobs'])} jobs, {len(result['skills'])} skills")
```

#### 2. Prompt Optimization (Next Step)
```python
from dspy.teleprompt import BootstrapFewShot

# Create training examples (10-20 resumes with expected outputs)
trainset = [...]

# Define accuracy metric
def extraction_accuracy(gold, pred, trace=None):
    score = 0
    if gold['person']['name'] == pred['person']['name']:
        score += 0.3
    if len(gold['jobs']) == len(pred['jobs']):
        score += 0.4
    # ... more checks
    return score

# Optimize prompts automatically
optimizer = BootstrapFewShot(metric=extraction_accuracy)
optimized_pipeline = optimizer.compile(
    student=ResumeExtractionModule(),
    trainset=trainset
)

# optimized_pipeline now has better prompts learned from examples
```

#### 3. RAG/Q&A System (Future)
```python
class ResumeQA(dspy.Module):
    """Answer questions about resume content."""

    def __init__(self):
        self.retrieve = dspy.Retrieve(k=3)  # Retrieve relevant sections
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        # Retrieve relevant resume chunks from vector DB
        context = self.retrieve(question).passages

        # Generate answer with reasoning
        return self.generate(context=context, question=question)

# Usage:
qa = ResumeQA()
answer = qa("What programming languages does this person know?")
print(answer.answer)
print(answer.rationale)  # See reasoning steps
```

#### 4. Evaluation Metrics
```python
from dspy.evaluate import Evaluate

# Evaluation dataset with gold labels
eval_examples = [
    {"resume": resume1, "expected_jobs": 3, "expected_skills": 12},
    # ... more examples
]

# Run systematic evaluation
evaluator = Evaluate(devset=eval_examples, metric=extraction_accuracy)

# Evaluate different backends
claude_score = evaluator(pipeline_with_claude)
openai_score = evaluator(pipeline_with_openai)

print(f"Claude accuracy: {claude_score}")
print(f"OpenAI accuracy: {openai_score}")
```

---

## Risk Mitigation

### Risk 1: JSONAdapter Too Strict
**Symptom**: Still get AdapterParseError even after Phase 1 fix

**Cause**: Built-in JSONAdapter requires ALL fields present, no defaults

**Solution**: Proceed to Phase 2 (custom JSONChatAdapter with defaults)

### Risk 2: Type Validation Failures
**Symptom**: Logs show "Type validation failed for 'field_name'"

**Cause**: LLM returns wrong type (e.g., `"jobs": "None found"` instead of `[]`)

**Solution**: JSONChatAdapter catches this and uses raw value as fallback. To fix root cause, improve prompt:
```python
# In ExtractResumeEntities signature, update field description:
jobs: list = dspy.OutputField(
    desc="List of job positions. MUST be an array, use [] if empty, never use string"
)
```

### Risk 3: Breaking SimplifiedExtractor
**Symptom**: Extraction fails when `ENABLE_DSPY=false`

**Cause**: Accidentally modified SimplifiedExtractor code

**Prevention**:
- Only modify DSPy path (create_extraction_pipeline)
- Test with `ENABLE_DSPY=false` after changes
- Run test_simplified_extractor_still_works()

### Risk 4: Missing Dependencies
**Symptom**: `ImportError: cannot import name 'json_repair'`

**Cause**: DSPy dependencies not fully installed

**Solution**:
```bash
cd backend
pip install dspy-ai[all]>=2.4.9
# or
pip install json-repair regex
```

---

## Success Criteria Checklist

After implementation, verify all these pass:

- [ ] ✅ No `AttributeError: 'str' object has no attribute 'get'`
- [ ] ✅ DSPy pipeline extracts all 7 entity types (person, jobs, skills, education, certifications, organizations)
- [ ] ✅ `extraction_result.person` is a dict (not a string)
- [ ] ✅ `extraction_result.jobs` is a list (not empty default)
- [ ] ✅ UI displays person name, email correctly
- [ ] ✅ UI shows jobs list with titles, companies
- [ ] ✅ Works with Claude backend (`LLM_PROVIDER=claude`)
- [ ] ✅ Works with OpenAI backend (`LLM_PROVIDER=openai`)
- [ ] ✅ SimplifiedExtractor fallback still works (`ENABLE_DSPY=false`)
- [ ] ✅ Logs show "Successfully parsed JSON with keys: [...]"
- [ ] ✅ Unit tests pass (test_json_adapter_parsing, test_simplified_extractor_still_works)
- [ ] ✅ Can run backend comparison experiment (test_extraction_comparison.py)

---

## Next Steps After Fix

### Immediate (Same Day)
1. ✅ Verify all success criteria
2. ✅ Run backend comparison experiment (Claude vs OpenAI)
3. ✅ Document findings in extraction quality comparison

### Short-Term (This Week)
4. Build evaluation dataset (10-20 resumes with expected outputs)
5. Create extraction_accuracy metric
6. Run baseline evaluation with current prompts
7. Try DSPy optimizers (BootstrapFewShot) to improve prompts
8. Measure improvement in extraction quality

### Medium-Term (This Month)
9. Build RAG/Q&A system over resume knowledge graphs
10. Experiment with dspy.ChainOfThought vs dspy.Predict
11. Create extraction quality dashboard
12. Document DSPy learnings for future reference

---

## Additional Resources

### DSPy Documentation
- **Adapters**: https://dspy-docs.vercel.app/docs/building-blocks/adapters
- **Optimizers**: https://dspy-docs.vercel.app/docs/building-blocks/optimizers
- **Evaluation**: https://dspy-docs.vercel.app/docs/building-blocks/metrics

### Codebase References
- **SimplifiedExtractor prompt**: `backend/resume_explorer/services/extraction_dspy.py` lines 140-257
- **ExtractResumeEntities signature**: `backend/resume_explorer/services/extraction_dspy.py` lines 17-57
- **DSPyLMAdapter**: `backend/resume_explorer/services/llm_client.py` lines 381-475

### Key DSPy Concepts
- **Signature**: Defines input/output contract (like a function signature)
- **Module**: Combines signatures with prompting strategies (Predict, ChainOfThought)
- **Adapter**: Bridges LLM response format to signature fields
- **Optimizer**: Automatically improves prompts using training examples
- **Metric**: Measures quality of outputs for evaluation

---

## Troubleshooting Guide

### Issue: "json_repair not found"
**Solution**: `pip install json-repair`

### Issue: "regex module not found"
**Solution**: `pip install regex` (note: not `re`, the `regex` library)

### Issue: Adapter still puts JSON into string field
**Symptom**: `person = '{"name": "...", ...}'` (string, not dict)

**Debug**:
1. Check logs for "Successfully parsed JSON" - if missing, JSON parsing failed
2. Check logs for "Field 'person' not in JSON response" - field name mismatch
3. Verify signature field names match JSON keys exactly (case-sensitive)
4. Print `parsed_json.keys()` in `_try_parse_json()` to see what LLM returned

### Issue: Type validation errors
**Symptom**: Logs show "Type validation failed for 'jobs'"

**Debug**:
1. Check what type LLM returned: `print(type(parsed_json['jobs']))`
2. Check what signature expects: `print(signature.output_fields['jobs'].annotation)`
3. Add better prompt hint in signature description
4. Or, modify `_map_json_to_fields()` to be more lenient

### Issue: SimplifiedExtractor broken
**Symptom**: Extraction fails when `ENABLE_DSPY=false`

**Debug**:
1. Check if SimplifiedExtractor code was modified (should not be)
2. Verify `create_extraction_pipeline(use_dspy=False)` returns SimplifiedExtractor
3. Run test_simplified_extractor_still_works()
4. Check logs for "Using simplified extraction pipeline"

---

**End of Implementation Plan**
