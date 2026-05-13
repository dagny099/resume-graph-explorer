# DSPy Status and Validation Plan

_Last updated: 2026-05-13_

## Summary

**DSPy in Resume Explorer is experimental and not production-validated.**

The codebase includes an implemented DSPy extraction path, but testing is incomplete across providers, concurrency conditions, and quality benchmarks.

## Current Recommendation

- **Production/default environments:** keep `ENABLE_DSPY=false`.
- **Testing sessions only:** enable DSPy explicitly with `use_dspy=true` on upload requests, or temporary environment overrides.

## Implemented vs Tested vs Planned

| Area | Implemented | Tested | Confidence | Notes |
|---|---|---|---|---|
| DSPy signatures (`ExtractResumeEntities`, `ExtractSkillHierarchy`) | Yes | Limited | Low-Medium | Structured schema extraction exists in code. |
| DSPy module (`ResumeExtractionModule`) | Yes | Limited | Low-Medium | Uses `dspy.Predict` and enrichment pass. |
| DSPy LM adapter (`DSPyLMAdapter`) | Yes | Limited | Low | Bridges provider backends to DSPy API. |
| Lenient parser fallback (`LenientChatAdapter`) | Yes | Limited | Medium | Best-effort parsing when strict DSPy parse fails. |
| Factory fallback to non-DSPy path | Yes | Basic | Medium | Falls back to `SimplifiedExtractor` on init failure. |
| Provider matrix (Claude/OpenAI/Ollama with DSPy) | Partial | Incomplete | Low | Needs repeatable compatibility test matrix. |
| Concurrency/threading behavior in deployed setup | Partial mitigation | Incomplete | Low | Known issue history; deployment should keep DSPy off by default. |
| DSPy optimizer/tuning (few-shot/teleprompt) | No | No | N/A | Planned future work. |

## Known Risks / Caveats

1. **Threading/concurrency sensitivity** in deployed architecture (historically observed).
2. **Provider-specific parse variance** can degrade structured extraction reliability.
3. **Quality benchmarks are not yet complete**, so extraction accuracy compared to non-DSPy route is not yet proven.

## Validation Checklist (for future contributors)

### Phase A: Functional Stability
- [ ] Verify DSPy extraction completes without exceptions on 20+ representative resumes.
- [ ] Confirm all required output fields are present (`person`, `jobs`, `skills`, `education`, `certifications`, `organizations`, `reasoning`).
- [ ] Validate fallback behavior when DSPy parsing fails.

### Phase B: Provider Compatibility
- [ ] Test Claude backend with DSPy enabled.
- [ ] Test OpenAI backend with DSPy enabled.
- [ ] Test Ollama backend with DSPy enabled.
- [ ] Record parse-failure rates and malformed-output rates per provider.

### Phase C: Concurrency / Deployment Safety
- [ ] Run concurrent upload tests (5, 10, 20 in-flight extractions).
- [ ] Confirm no cross-request contamination in DSPy context usage.
- [ ] Confirm no increased document error rate vs non-DSPy baseline.

### Phase D: Quality Evaluation
- [ ] Compare DSPy vs non-DSPy extraction on labeled sample set.
- [ ] Track precision/recall (or rubric-based scores) for each entity type.
- [ ] Decide go/no-go threshold for enabling DSPy by default.

## Exit Criteria to Remove “Experimental” Label

Only remove the experimental label when all are true:

1. Provider matrix completed with acceptable error rates.
2. Concurrency tests show stability comparable to non-DSPy route.
3. Quality benchmarks are documented and meet target thresholds.
4. Deployment defaults and docs are updated consistently.

## Related Files

- `backend/resume_explorer/services/extraction_dspy.py`
- `backend/resume_explorer/services/llm_client.py`
- `backend/resume_explorer/api/routes.py`
- `backend/resume_explorer/api/app.py`
- `docs/API.md`
- `README.md`
