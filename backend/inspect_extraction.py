#!/usr/bin/env python3
"""
Inspection tool for reviewing extraction results.

Usage:
    python inspect_extraction.py <session_id>
    python inspect_extraction.py --latest
"""

import sys
import json
from pathlib import Path
from datetime import datetime


def inspect_session(session_id: str):
    """Inspect a specific session's extraction results."""

    # Find session data
    data_path = Path("data")
    sessions_index = data_path / "sessions.index.json"

    if not sessions_index.exists():
        print(f"❌ Sessions index not found at {sessions_index}")
        return

    with open(sessions_index) as f:
        index = json.load(f)

    # Find session
    session = None
    for s in index['sessions']:
        if s['id'] == session_id or s['name'] == session_id:
            session = s
            break

    if not session:
        print(f"❌ Session '{session_id}' not found")
        print("\nAvailable sessions:")
        for s in index['sessions']:
            print(f"  - {s['name']} ({s['id']})")
        return

    print(f"\n{'='*80}")
    print(f"📊 SESSION: {session['name']}")
    print(f"{'='*80}")
    print(f"ID: {session['id']}")
    print(f"Created: {session['created_at']}")
    print(f"Documents: {len(session['documents'])}")
    print()

    # Inspect each document
    for doc_id in session['documents']:
        # Find document in index
        doc = next((d for d in index['documents'] if d['id'] == doc_id), None)
        if not doc:
            continue

        print(f"\n{'-'*80}")
        print(f"📄 DOCUMENT: {doc['filename']}")
        print(f"{'-'*80}")
        print(f"Status: {doc['status']}")
        print(f"Uploaded: {doc['upload_date']}")

        if doc['status'] == 'error':
            print(f"❌ Error: {doc.get('error_message', 'Unknown error')}")
            continue

        # Load entities
        entities_file = data_path / "sessions" / session['id'] / "extracted" / f"{doc_id}.json"
        if not entities_file.exists():
            print("⚠️  No extracted entities found")
            continue

        with open(entities_file) as f:
            entities = json.load(f)

        # Display entity summary
        print("\n✅ EXTRACTION SUMMARY:")

        person = entities.get('person', {})
        if person:
            print(f"  👤 Person: {person.get('name', 'N/A')}")
            if person.get('email'):
                print(f"     Email: {person['email']}")
            if person.get('location'):
                print(f"     Location: {person['location']}")

        jobs = entities.get('jobs', [])
        print(f"\n  💼 Jobs: {len(jobs)}")
        for i, job in enumerate(jobs[:5], 1):  # Show first 5
            print(f"     {i}. {job.get('title', 'N/A')} at {job.get('organization_id', 'N/A')}")
            if job.get('start_date'):
                print(f"        {job['start_date']} → {job.get('end_date', 'Present')}")
        if len(jobs) > 5:
            print(f"     ... and {len(jobs) - 5} more")

        skills = entities.get('skills', [])
        print(f"\n  🎯 Skills: {len(skills)}")
        for i, skill in enumerate(skills[:10], 1):  # Show first 10
            label = skill.get('label', 'N/A')
            cat = skill.get('category', '')
            prof = skill.get('proficiency_level', '')
            print(f"     {i}. {label}", end='')
            if cat:
                print(f" ({cat})", end='')
            if prof:
                print(f" - {prof}", end='')
            print()
        if len(skills) > 10:
            print(f"     ... and {len(skills) - 10} more")

        education = entities.get('education', [])
        if education:
            print(f"\n  🎓 Education: {len(education)}")
            for i, edu in enumerate(education, 1):
                print(f"     {i}. {edu.get('degree_type', 'N/A')} in {edu.get('field_of_study', 'N/A')}")
                print(f"        at {edu.get('institution_id', 'N/A')}")

        certifications = entities.get('certifications', [])
        if certifications:
            print(f"\n  📜 Certifications: {len(certifications)}")
            for i, cert in enumerate(certifications, 1):
                print(f"     {i}. {cert.get('name', 'N/A')}")
                if cert.get('issuing_organization'):
                    print(f"        by {cert['issuing_organization']}")

        organizations = entities.get('organizations', [])
        if organizations:
            print(f"\n  🏢 Organizations: {len(organizations)}")
            for i, org in enumerate(organizations, 1):
                org_type = org.get('org_type', 'N/A')
                print(f"     {i}. {org.get('name', 'N/A')} ({org_type})")

        # Show metadata
        metadata = entities.get('metadata', {})
        if metadata:
            print(f"\n  ℹ️  Metadata:")
            print(f"     Extraction Time: {metadata.get('extraction_timestamp', 'N/A')}")
            print(f"     Using DSPy: {metadata.get('use_dspy', False)}")
            reasoning = metadata.get('reasoning', '')
            if reasoning and len(reasoning) > 100:
                print(f"     Reasoning: {reasoning[:100]}...")
            elif reasoning:
                print(f"     Reasoning: {reasoning}")

    print(f"\n{'='*80}\n")


def inspect_latest():
    """Inspect the most recently updated session."""
    data_path = Path("data")
    sessions_index = data_path / "sessions.index.json"

    if not sessions_index.exists():
        print(f"❌ Sessions index not found")
        return

    with open(sessions_index) as f:
        index = json.load(f)

    if not index['sessions']:
        print("❌ No sessions found")
        return

    # Sort by updated_at
    latest = max(index['sessions'], key=lambda s: s['updated_at'])
    inspect_session(latest['id'])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python inspect_extraction.py <session_id_or_name>")
        print("  python inspect_extraction.py --latest")
        sys.exit(1)

    arg = sys.argv[1]
    if arg == '--latest':
        inspect_latest()
    else:
        inspect_session(arg)
