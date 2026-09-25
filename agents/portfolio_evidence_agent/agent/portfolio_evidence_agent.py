from datetime import datetime, timezone

from .nlp_extractor import NLPExtractor
from .reconciler import Reconciler


class PortfolioEvidenceAgent:
    VERSION = "1.0.0"

    def __init__(
        self,
        taxonomy_path="data/skill_taxonomy.json",
        use_llm=False
    ):
        # NLP extractor
        self.nlp = NLPExtractor(taxonomy_path)

        # Reconciler
        self.reconciler = Reconciler(
            self.nlp.taxonomy
        )

        # LLM is disabled for now
        self.use_llm = use_llm
        self.llm = None

    def process(self, profile: dict) -> dict:
        """
        Process a freelancer profile and return
        structured skill evidence.
        """

        ner_items = []
        llm_items = []
        notes = []
        unmapped = []

        # Go through every source in the profile
        for text, source_type, source_ref in self._iter_sources(profile):

            # Empty or extremely short source
            if not text or len(text.strip()) < 10:
                notes.append(
                    f"{source_ref}: empty or too short to extract from."
                )
                continue

            # Short source warning
            if len(text.split()) < 20:
                notes.append(
                    f"{source_ref}: very short (<20 words) — "
                    f"low evidence density."
                )

            # NLP extraction
            ner_items.extend(
                self.nlp.extract(
                    text,
                    source_type,
                    source_ref
                )
            )

            # Candidate terms not found in taxonomy
            unmapped.extend(
                self.nlp.candidate_terms(text)
            )

        # Merge and clean evidence
        evidence_items, unmapped_from_reconciler = (
            self.reconciler.merge(
                ner_items,
                llm_items
            )
        )

        if not evidence_items:
            notes.append(
                "No extractable skill evidence found in this profile."
            )

        return {
            "freelancer_id": profile.get("freelancer_id"),
            "agent": "portfolio_evidence_agent",
            "agent_version": self.VERSION,
            "extracted_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "evidence_items": evidence_items,
            "unmapped_terms": list(
                set(
                    unmapped_from_reconciler + unmapped
                )
            )[:20],
            "processing_notes": notes
        }

    def _iter_sources(self, profile):
        """
        Convert all supported profile sections into
        text sources for extraction.
        """

        # Portfolio projects
        for project in profile.get(
            "portfolio_projects",
            []
        ):
            text = (
                f"{project.get('title', '')}. "
                f"{project.get('description', '')}"
            )

            yield (
                text,
                "portfolio_project",
                project["project_id"]
            )

        # Certificates
        for certificate in profile.get(
            "certificates",
            []
        ):
            text = (
                f"{certificate.get('title', '')}. "
                f"{certificate.get('description', '')}"
            )

            yield (
                text,
                "certificate",
                certificate["certificate_id"]
            )

        # Code samples
        for sample in profile.get(
            "code_samples",
            []
        ):
            text = (
                f"Language: {sample.get('language', '')}. "
                f"{sample.get('snippet', '')}"
            )

            yield (
                text,
                "code_sample",
                sample["sample_id"]
            )

        # Work descriptions
        for work in profile.get(
            "work_descriptions",
            []
        ):
            yield (
                work.get("description", ""),
                "work_description",
                work["work_id"]
            )