"""
PipelineService — In-App Post-Export Analysis Pipeline

Wraps the offline tools (graph_analyzer, narrative_synthesizer) for use
within the Flask API. Manages per-session insight storage and emits
WebSocket events for real-time progress.

Tool modules are loaded via importlib.util.spec_from_file_location() to
avoid any sys.path side effects. The tools remain unchanged and runnable
as standalone CLI scripts.

Narrative synthesis uses the app's existing LLMClient.generate() instead
of narrative_synthesizer.call_llm(), which calls sys.exit() on errors.
"""

import importlib.util
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ..models import Person, Job, Skill, Education, Certification, Organization
from ..graph import RDFGraphBuilder
from ..utils.logger import logger


class PipelineService:
    """
    Orchestrates the post-export graph analysis pipeline within the app.

    Stores all outputs under sessions/{id}/insights/ to keep session data
    co-located. The flow is:

        _ensure_jsonld()           → sessions/{id}/graph.jsonld
        [optional normalization]   → sessions/{id}/graph_normalized.jsonld
        graph_analyzer.run_pipeline() → sessions/{id}/insights/*.md (6 files)
        narrative_synthesizer      → sessions/{id}/insights/career_narrative_*.md
    """

    ANALYSIS_TYPES = [
        'skill_gap',
        'career_topology',
        'tech_evolution',
        'hierarchy_map',
        'esco_coverage',
        'role_progression',
    ]

    ANALYSIS_TITLES = {
        'skill_gap':       'Hidden Skills — Claimed vs. Used Analysis',
        'career_topology': 'Career Topology — What Connects Different Roles',
        'tech_evolution':  'Technology Evolution — How the Toolkit Changed Over Time',
        'hierarchy_map':   'Skill Hierarchy — SKOS Taxonomy Structure',
        'esco_coverage':   'ESCO Interoperability — Global Skill Identifiability',
        'role_progression':'Role Progression — Career Arc and Trajectory',
    }

    def __init__(self, session_store, data_path: str, llm_client=None):
        self.session_store = session_store
        self.data_path = Path(data_path)
        self.llm_client = llm_client
        self._tools_dir = Path(__file__).parent.parent.parent / 'tools'

    # ─── Path helpers ────────────────────────────────────────────────────────

    def _insights_dir(self, session_id: str) -> Path:
        return self.data_path / 'sessions' / session_id / 'insights'

    def _jsonld_path(self, session_id: str) -> Path:
        return self.data_path / 'sessions' / session_id / 'graph.jsonld'

    # ─── Tool loader ─────────────────────────────────────────────────────────

    def _load_tool(self, tool_name: str):
        """
        Load a tool module by absolute file path.

        Uses importlib.util.spec_from_file_location() so there are no
        sys.path side effects. Each call loads a fresh module instance.
        """
        tool_path = self._tools_dir / f'{tool_name}.py'
        if not tool_path.exists():
            raise FileNotFoundError(f"Tool not found: {tool_path}")

        spec = importlib.util.spec_from_file_location(
            f"resume_explorer_tools.{tool_name}",
            tool_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # ─── JSON-LD bootstrap ───────────────────────────────────────────────────

    def _ensure_jsonld(self, session_id: str) -> Path:
        """
        Return the session's graph.jsonld path, building it if needed.

        Replicates the entity-collect + RDFGraphBuilder pattern from
        routes.export_session_graph() without touching Flask request context.
        """
        jsonld_path = self._jsonld_path(session_id)
        if jsonld_path.exists():
            return jsonld_path

        logger.info(f"graph.jsonld not found for session {session_id}, building now")

        documents = self.session_store.get_session_documents(session_id)
        complete_docs = [d for d in documents if d.status == 'complete']

        if not complete_docs:
            raise ValueError(f"Session {session_id} has no completed extractions")

        all_persons, all_jobs, all_skills = [], [], []
        all_education, all_certifications, all_organizations = [], [], []

        for doc in complete_docs:
            entities = self.session_store.load_extracted_entities(doc.id)
            if not entities:
                continue

            person = entities.get('person')
            if person and isinstance(person, dict):
                all_persons.append(Person.from_dict(person))

            for j in entities.get('jobs', []):
                all_jobs.append(Job.from_dict(j) if isinstance(j, dict) else j)

            for s in entities.get('skills', []):
                all_skills.append(Skill.from_dict(s) if isinstance(s, dict) else s)

            for e in entities.get('education', []):
                all_education.append(Education.from_dict(e) if isinstance(e, dict) else e)

            for c in entities.get('certifications', []):
                all_certifications.append(Certification.from_dict(c) if isinstance(c, dict) else c)

            for o in entities.get('organizations', []):
                all_organizations.append(Organization.from_dict(o) if isinstance(o, dict) else o)

        person = all_persons[0] if all_persons else Person(name="Unknown")
        builder = RDFGraphBuilder()
        builder.build_from_entities(
            person=person,
            jobs=all_jobs,
            skills=all_skills,
            education=all_education,
            certifications=all_certifications,
            organizations=all_organizations,
        )
        builder.export_jsonld(str(jsonld_path))
        logger.info(f"Built graph.jsonld for session {session_id}: {jsonld_path}")
        return jsonld_path

    # ─── Pipeline status ─────────────────────────────────────────────────────

    def get_pipeline_status(self, session_id: str) -> dict:
        """Return availability of analyses and narratives for a session."""
        insights_dir = self._insights_dir(session_id)
        available = [
            t for t in self.ANALYSIS_TYPES
            if (insights_dir / f'{t}.md').exists()
        ]
        return {
            'insights_available': len(available),
            'insights_total': 6,
            'insights_list': available,
            'narratives_conservative': (insights_dir / 'career_narrative_conservative.md').exists(),
            'narratives_exploratory':  (insights_dir / 'career_narrative_exploratory.md').exists(),
        }

    # ─── Step 1: Graph analysis ──────────────────────────────────────────────

    def run_analysis(
        self,
        session_id: str,
        normalize: bool = False,
        emit_fn: Optional[Callable] = None,
    ) -> list:
        """
        Run graph_analyzer on the session graph, producing 6 insight .md files.

        Args:
            session_id: Session to analyze.
            normalize:  If True, run the offline entity_normalizer (deterministic
                        phases only, --provider mock) before graph analysis.
            emit_fn:    Callable(event_name, data) for WebSocket progress events.

        Returns:
            List of AnalysisDocument objects from graph_analyzer.run_pipeline().
        """
        emit = emit_fn or (lambda event, data: None)

        emit('pipeline_analysis_started', {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
        })

        # 1. Ensure JSON-LD exists on disk
        try:
            emit('pipeline_analysis_progress', {
                'session_id': session_id,
                'message': 'Preparing graph export…',
            })
            jsonld_path = self._ensure_jsonld(session_id)
        except Exception as e:
            logger.error(f"Failed to build graph.jsonld for {session_id}: {e}")
            emit('pipeline_analysis_error', {'session_id': session_id, 'error': str(e)})
            raise

        # 2. Optional deterministic normalization
        if normalize:
            emit('pipeline_analysis_progress', {
                'session_id': session_id,
                'message': 'Normalizing entity labels (deterministic pass)…',
            })
            normalized_path = jsonld_path.parent / 'graph_normalized.jsonld'
            normalizer_script = str(self._tools_dir / 'entity_normalizer.py')
            try:
                result = subprocess.run(
                    [
                        sys.executable, normalizer_script,
                        '--input', str(jsonld_path),
                        '--output', str(normalized_path),
                        '--provider', 'mock',
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    jsonld_path = normalized_path
                    logger.info(f"Normalization succeeded for {session_id}")
                else:
                    logger.warning(
                        f"Normalization failed for {session_id} (exit {result.returncode}), "
                        f"continuing without: {result.stderr[:200]}"
                    )
            except Exception as e:
                logger.warning(f"Normalization subprocess error for {session_id}: {e}, continuing")

        # 3. Run graph analysis
        emit('pipeline_analysis_progress', {
            'session_id': session_id,
            'message': 'Running 6 structural analyses…',
        })

        insights_dir = self._insights_dir(session_id)
        insights_dir.mkdir(parents=True, exist_ok=True)

        try:
            graph_analyzer = self._load_tool('graph_analyzer')
            docs = graph_analyzer.run_pipeline(str(jsonld_path), str(insights_dir))
        except Exception as e:
            logger.error(f"graph_analyzer failed for {session_id}: {e}")
            emit('pipeline_analysis_error', {'session_id': session_id, 'error': str(e)})
            raise

        emit('pipeline_analysis_complete', {
            'session_id': session_id,
            'insights_count': len(docs),
        })
        logger.info(f"Analysis complete for {session_id}: {len(docs)} insights")
        return docs

    # ─── Step 2: Narrative synthesis ─────────────────────────────────────────

    def run_synthesis(
        self,
        session_id: str,
        provider: str = 'anthropic',
        model: Optional[str] = None,
        emit_fn: Optional[Callable] = None,
    ) -> dict:
        """
        Generate Conservative and Exploratory career narratives from the 6 insights.

        Uses the app's LLMClient.generate() rather than narrative_synthesizer.call_llm()
        to avoid sys.exit() on API errors.

        Args:
            session_id: Session to synthesize narratives for.
            provider:   LLM provider ('anthropic' or 'openai').
            model:      Specific model override (None = provider default).
            emit_fn:    Callable for WebSocket progress events.

        Returns:
            Dict with 'conservative' and 'exploratory' narrative strings.
        """
        emit = emit_fn or (lambda event, data: None)

        insights_dir = self._insights_dir(session_id)
        if not insights_dir.exists() or not any(insights_dir.glob('*.md')):
            raise ValueError(
                "No insight files found. Run graph analysis (Step 1) first."
            )

        if self.llm_client is None:
            raise ValueError("No LLM client configured. Check LLM_PROVIDER in .env.")

        # Load helper functions from narrative_synthesizer (not call_llm — it uses sys.exit)
        try:
            ns = self._load_tool('narrative_synthesizer')
        except Exception as e:
            logger.error(f"Failed to load narrative_synthesizer: {e}")
            emit('pipeline_synthesis_error', {'session_id': session_id, 'error': str(e)})
            raise

        emit('pipeline_synthesis_started', {
            'session_id': session_id,
            'provider': provider,
        })

        # Load and format the 6 analyses
        analyses = ns.load_analyses(insights_dir)
        if not analyses:
            err = "No analysis files readable in insights directory"
            emit('pipeline_synthesis_error', {'session_id': session_id, 'error': err})
            raise ValueError(err)

        person_name = ns.extract_person_name(analyses)
        formatted = ns.format_analyses_for_prompt(analyses)
        source_list = list(analyses.keys())

        effective_model = model or (
            'claude-sonnet-4-20250514' if provider == 'anthropic' else 'gpt-4o'
        )

        results = {}
        variants = [
            ('conservative', ns.CONSERVATIVE_PROMPT),
            ('exploratory',  ns.EXPLORATORY_PROMPT),
        ]

        for variant_name, prompt_template in variants:
            emit('pipeline_synthesis_progress', {
                'session_id': session_id,
                'message': f'Generating {variant_name} narrative…',
                'variant': variant_name,
            })

            user_prompt = prompt_template.format(analyses=formatted)

            try:
                narrative = self.llm_client.generate(
                    prompt=user_prompt,
                    system_prompt=ns.SYSTEM_PROMPT,
                    max_tokens=4000,
                )
            except Exception as e:
                logger.error(f"LLM call failed for {variant_name} narrative: {e}")
                emit('pipeline_synthesis_error', {'session_id': session_id, 'error': str(e)})
                raise

            front_matter = ns.build_front_matter(
                variant=variant_name,
                person_name=person_name,
                source_analyses=source_list,
                provider=provider,
                model=effective_model,
            )

            output_path = insights_dir / f'career_narrative_{variant_name}.md'
            output_path.write_text(f"{front_matter}\n\n{narrative}\n")
            results[variant_name] = narrative
            logger.info(f"Wrote {output_path} ({len(narrative)} chars)")

        emit('pipeline_synthesis_complete', {'session_id': session_id})
        logger.info(f"Synthesis complete for {session_id}")
        return results

    # ─── Retrieval ───────────────────────────────────────────────────────────

    def get_insights(self, session_id: str) -> dict:
        """Return all 6 analysis documents (with content if available)."""
        insights_dir = self._insights_dir(session_id)
        analyses = []
        for t in self.ANALYSIS_TYPES:
            path = insights_dir / f'{t}.md'
            analyses.append({
                'type': t,
                'title': self.ANALYSIS_TITLES[t],
                'available': path.exists(),
                'content': path.read_text() if path.exists() else None,
            })
        return {'analyses': analyses}

    def get_narratives(self, session_id: str) -> dict:
        """Return conservative and exploratory narrative content (or None)."""
        insights_dir = self._insights_dir(session_id)
        conservative = insights_dir / 'career_narrative_conservative.md'
        exploratory  = insights_dir / 'career_narrative_exploratory.md'
        return {
            'conservative': conservative.read_text() if conservative.exists() else None,
            'exploratory':  exploratory.read_text()  if exploratory.exists()  else None,
        }
