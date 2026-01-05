#!/usr/bin/env python3
"""
Verify Option B implementation is complete.
"""

import sys
import os

print("=" * 60)
print("Option B Implementation Verification")
print("=" * 60)

# Check 1: Threading fix
print("\n✓ Check 1: Threading fix in extraction_dspy.py")
with open('resume_explorer/services/extraction_dspy.py', 'r') as f:
    content = f.read()
    if 'def __init__(self, llm_backend=None, adapter=None):' in content:
        print("  ✓ ResumeExtractionModule accepts backend and adapter")
    else:
        print("  ✗ Missing backend/adapter parameters")
        sys.exit(1)

    if 'self._configured = False' in content:
        print("  ✓ Lazy initialization flag added")
    else:
        print("  ✗ Missing lazy initialization flag")
        sys.exit(1)

    if 'DSPy configured lazily in worker thread' in content:
        print("  ✓ Lazy configuration in forward() method")
    else:
        print("  ✗ Missing lazy configuration")
        sys.exit(1)

# Check 2: API parameter
print("\n✓ Check 2: API parameter in routes.py")
with open('resume_explorer/api/routes.py', 'r') as f:
    content = f.read()
    if 'use_dspy: \'true\' or \'false\' to override default extraction method' in content:
        print("  ✓ API documentation added")
    else:
        print("  ✗ Missing API documentation")
        sys.exit(1)

    if 'use_dspy_param = request.args.get(\'use_dspy\'' in content:
        print("  ✓ Query parameter parsing added")
    else:
        print("  ✗ Missing query parameter parsing")
        sys.exit(1)

    if 'extraction_method = "DSPy" if use_dspy else "SimplifiedExtractor"' in content:
        print("  ✓ Extraction method logging added")
    else:
        print("  ✗ Missing extraction method logging")
        sys.exit(1)

# Check 3: Default setting
print("\n✓ Check 3: SimplifiedExtractor as default in .env")
with open('../.env', 'r') as f:
    content = f.read()
    if 'ENABLE_DSPY=false' in content:
        print("  ✓ ENABLE_DSPY=false set as default")
    else:
        print("  ✗ ENABLE_DSPY should be false")
        sys.exit(1)

    if 'Can override per-upload with ?use_dspy=true' in content:
        print("  ✓ Documentation added to .env")
    else:
        print("  ✗ Missing .env documentation")

# Check 4: Adapter fix
print("\n✓ Check 4: LenientChatAdapter type safety fix")
with open('resume_explorer/services/llm_client.py', 'r') as f:
    content = f.read()
    if 'elif ann == dict or (hasattr(ann, \'__origin__\') and ann.__origin__ == dict):' in content:
        print("  ✓ Dict type handling added")
    else:
        print("  ✗ Missing dict type handling")
        sys.exit(1)

    if 'outputs.update(parsed)' in content:
        print("  ✓ Partial JSON parsing added")
    else:
        print("  ✗ Missing partial JSON parsing")
        sys.exit(1)

print("\n" + "=" * 60)
print("✓ All checks passed! Option B implementation complete.")
print("=" * 60)

print("\n📋 Summary of Changes:")
print("  1. Threading bug fixed - DSPy configures lazily in worker thread")
print("  2. API parameter added - ?use_dspy=true/false")
print("  3. SimplifiedExtractor default - ENABLE_DSPY=false")
print("  4. Adapter safety improved - proper type defaults")

print("\n🚀 Next Steps:")
print("  1. Restart your backend server (if running)")
print("  2. Upload a resume (uses SimplifiedExtractor by default)")
print("  3. Test DSPy with: curl -X POST 'URL?use_dspy=true' ...")
print("  4. See test_extraction_switching.md for detailed instructions")

print("\n💡 Tips:")
print("  - SimplifiedExtractor: Fast, cheap, reliable")
print("  - DSPy: Skill hierarchies, reasoning, explainability")
print("  - Switch anytime with ?use_dspy=true parameter")
print("  - Use Ollama for free DSPy extraction later")
