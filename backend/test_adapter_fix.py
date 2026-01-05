#!/usr/bin/env python3
"""
Quick test to verify the LenientChatAdapter fix.
Tests that it returns proper types even when parsing fails.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resume_explorer'))

from resume_explorer.services.llm_client import LenientChatAdapter
from resume_explorer.services.extraction_dspy import ExtractResumeEntities


def test_adapter_fallback():
    """Test that adapter returns proper types on parse failure."""
    adapter = LenientChatAdapter()
    signature = ExtractResumeEntities

    # Simulate truncated/invalid response like your error
    bad_completion = "{"

    print("Testing LenientChatAdapter with truncated response: '{'")
    print("-" * 60)

    try:
        result = adapter.parse(signature, bad_completion)
        print("✓ Adapter returned result without crashing")
        print(f"\nResult keys: {list(result.keys())}")
        print("\nField types:")
        for field, value in result.items():
            print(f"  {field}: {type(value).__name__} = {repr(value)[:100]}")

        # Verify critical fields are correct types
        assert isinstance(result.get('person'), dict), "person must be dict"
        assert isinstance(result.get('jobs'), list), "jobs must be list"
        assert isinstance(result.get('skills'), list), "skills must be list"
        assert isinstance(result.get('education'), list), "education must be list"
        assert isinstance(result.get('certifications'), list), "certifications must be list"
        assert isinstance(result.get('organizations'), list), "organizations must be list"
        assert isinstance(result.get('reasoning'), str), "reasoning must be str"

        print("\n✓ All field types are correct!")
        print("\n✓ Fix verified: Adapter will no longer crash on bad LLM responses")
        return True

    except AttributeError as e:
        print(f"\n✗ AttributeError still occurs: {e}")
        return False
    except AssertionError as e:
        print(f"\n✗ Type assertion failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_adapter_fallback()
    sys.exit(0 if success else 1)
