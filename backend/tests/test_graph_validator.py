"""
Tests for the semantic integrity graph validator.

Covers:
- A well-formed graph validates cleanly (no errors)
- Dangling relationship references are reported as errors
- Missing/empty skos:prefLabel is reported as an error
- Near-duplicate skill labels are reported as warnings
- Jobs missing organization/dates/technologies produce warnings
- Completeness checks against raw extraction counts
"""

import pytest
from datetime import date

from resume_explorer.graph import RDFGraphBuilder
from resume_explorer.graph.graph_validator import GraphValidator
from resume_explorer.models import (
    Certification, Education, Job, Organization, Person, Skill,
)


def build_clean_graph() -> RDFGraphBuilder:
    """A complete, internally consistent graph."""
    builder = RDFGraphBuilder()
    builder.build_from_entities(
        person=Person(
            id="person-1", label="Test Person", name="Test Person",
            jobs=["job-1"], skills=["skill-1"],
            education=["edu-1"], certifications=["cert-1"],
        ),
        jobs=[Job(
            id="job-1", label="Engineer", title="Engineer",
            organization_id="org-1", start_date=date(2020, 1, 1),
            skills_used=["skill-1"], technologies_used=["Python"],
        )],
        skills=[Skill(id="skill-1", label="Python")],
        education=[Education(
            id="edu-1", label="BS in CS",
            degree_type="BS", field_of_study="CS", institution_id="org-1",
        )],
        certifications=[Certification(id="cert-1", label="Cert", name="Cert")],
        organizations=[Organization(id="org-1", label="Tech Corp", name="Tech Corp")],
    )
    return builder


def checks_in(issues):
    return {i['check'] for i in issues}


class TestCleanGraph:
    def test_valid_with_no_errors(self):
        report = GraphValidator(build_clean_graph().graph).validate()
        assert report['valid'] is True
        assert report['errors'] == []

    def test_stats_reported(self):
        report = GraphValidator(build_clean_graph().graph).validate()
        counts = report['stats']['entity_counts']
        assert counts['person'] == 1
        assert counts['job'] == 1
        assert counts['skill'] == 1
        assert report['stats']['triple_count'] > 0

    def test_clean_graph_passes_completeness_check(self):
        report = GraphValidator(build_clean_graph().graph).validate(
            extracted_counts={
                'person': 1, 'job': 1, 'skill': 1,
                'education': 1, 'certification': 1, 'organization': 1,
            }
        )
        assert report['valid'] is True
        assert checks_in(report['warnings']) & {'low_entity_count'} == set()


class TestDanglingReferences:
    def test_person_referencing_missing_job_is_error(self):
        builder = RDFGraphBuilder()
        builder.add_person(Person(
            id="person-1", label="P", name="P", jobs=["job-does-not-exist"],
        ))
        report = GraphValidator(builder.graph).validate()

        assert report['valid'] is False
        assert 'dangling_reference' in checks_in(report['errors'])

    def test_job_referencing_missing_org_is_error(self):
        builder = RDFGraphBuilder()
        builder.add_job(Job(
            id="job-1", label="Engineer", title="Engineer",
            organization_id="org-never-added",
            start_date=date(2020, 1, 1), technologies_used=["Python"],
        ))
        report = GraphValidator(builder.graph).validate()

        assert report['valid'] is False
        dangling = [e for e in report['errors'] if e['check'] == 'dangling_reference']
        assert any('org-never-added' in e['message'] for e in dangling)

    def test_skos_hierarchy_dangling_is_warning_not_error(self):
        builder = RDFGraphBuilder()
        builder.add_skill(Skill(
            id="skill-1", label="Python",
            broader_concepts=["concept-not-materialized"],
        ))
        report = GraphValidator(builder.graph).validate()

        assert 'skos_dangling' in checks_in(report['warnings'])
        assert 'dangling_reference' not in checks_in(report['errors'])


class TestLabels:
    def test_empty_skill_label_is_error(self):
        builder = RDFGraphBuilder()
        builder.add_skill(Skill(id="skill-1", label=""))
        report = GraphValidator(builder.graph).validate()

        assert report['valid'] is False
        assert 'missing_label' in checks_in(report['errors'])


class TestNearDuplicateSkills:
    def test_punctuation_variants_flagged(self):
        builder = RDFGraphBuilder()
        builder.add_skill(Skill(id="skill-1", label="Scikit-Learn"))
        builder.add_skill(Skill(id="skill-2", label="scikit learn"))
        report = GraphValidator(builder.graph).validate()

        dupes = [w for w in report['warnings'] if w['check'] == 'near_duplicate_skills']
        assert len(dupes) == 1
        assert 'Scikit-Learn' in dupes[0]['message']

    def test_distinct_skills_not_flagged(self):
        builder = RDFGraphBuilder()
        builder.add_skill(Skill(id="skill-1", label="Python"))
        builder.add_skill(Skill(id="skill-2", label="Java"))
        report = GraphValidator(builder.graph).validate()

        assert 'near_duplicate_skills' not in checks_in(report['warnings'])


class TestJobChecks:
    def test_bare_job_produces_three_warnings(self):
        builder = RDFGraphBuilder()
        builder.add_job(Job(id="job-1", label="Mystery Role", title="Mystery Role"))
        report = GraphValidator(builder.graph).validate()

        warning_checks = checks_in(report['warnings'])
        assert 'job_missing_organization' in warning_checks
        assert 'job_missing_dates' in warning_checks
        assert 'job_no_technologies' in warning_checks

    def test_complete_job_produces_no_job_warnings(self):
        report = GraphValidator(build_clean_graph().graph).validate()
        warning_checks = checks_in(report['warnings'])
        assert not warning_checks & {
            'job_missing_organization', 'job_missing_dates', 'job_no_technologies',
        }


class TestCompleteness:
    def test_type_entirely_missing_is_error(self):
        builder = RDFGraphBuilder()
        builder.add_skill(Skill(id="skill-1", label="Python"))
        report = GraphValidator(builder.graph).validate(
            extracted_counts={'skill': 1, 'certification': 3}
        )

        assert report['valid'] is False
        missing = [e for e in report['errors'] if e['check'] == 'type_missing_in_export']
        assert len(missing) == 1
        assert 'certification' in missing[0]['message']

    def test_losing_more_than_half_is_warning(self):
        builder = RDFGraphBuilder()
        builder.add_skill(Skill(id="skill-1", label="Python"))
        report = GraphValidator(builder.graph).validate(extracted_counts={'skill': 5})

        assert 'low_entity_count' in checks_in(report['warnings'])

    def test_dedup_losses_under_half_not_flagged(self):
        builder = RDFGraphBuilder()
        builder.add_skill(Skill(id="skill-1", label="Python"))
        builder.add_skill(Skill(id="skill-2", label="python"))  # dedups to 1 node
        report = GraphValidator(builder.graph).validate(extracted_counts={'skill': 2})

        assert 'low_entity_count' not in checks_in(report['warnings'])

    def test_no_person_is_warning(self):
        builder = RDFGraphBuilder()
        builder.add_skill(Skill(id="skill-1", label="Python"))
        report = GraphValidator(builder.graph).validate()

        assert 'no_person' in checks_in(report['warnings'])
