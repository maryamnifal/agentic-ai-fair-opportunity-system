from datetime import datetime, timezone

from .nlp_extractor import NLPExtractor
from .llm_interpreter import LLMInterpreter
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

        # LLM interpreter is optional
        self.llm = (
            LLMInterpreter()
            if use_llm
            else None
        )

        # Reconciler combines NLP + LLM results
        self.reconciler = Reconciler(
            self.nlp.taxonomy
        )

        self.use_llm = use_llm


    def process(self, profile: dict) -> dict:
        """
        Process freelancer material and return
        structured skill evidence.
        """

        ner_items = []
        llm_items = []
        notes = []
        unmapped = []

        known_skills = list(
            self.nlp.taxonomy.keys()
        )


        for (
            text,
            source_type,
            source_ref
        ) in self._iter_sources(profile):

            # Skip empty or extremely short content
            if not text or len(text.strip()) < 10:

                notes.append(
                    f"{source_ref}: empty or too short to extract from."
                )

                continue


            # Record low-evidence-density input
            if len(text.split()) < 20:

                notes.append(
                    f"{source_ref}: very short (<20 words) — "
                    f"low evidence density."
                )


            # -------------------------
            # NLP extraction
            # -------------------------

            ner_items.extend(
                self.nlp.extract(
                    text,
                    source_type,
                    source_ref
                )
            )


            # Candidate terms not already recognised
            unmapped.extend(
                self.nlp.candidate_terms(text)
            )


            # -------------------------
            # LLM interpretation
            # -------------------------

            if self.use_llm and self.llm:

                llm_items.extend(
                    self._safe_llm(
                        text,
                        source_type,
                        source_ref,
                        known_skills
                    )
                )


        # Merge NLP and LLM evidence
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
            "freelancer_id":
                profile.get("freelancer_id"),

            "agent":
                "portfolio_evidence_agent",

            "agent_version":
                self.VERSION,

            "extracted_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "evidence_items":
                evidence_items,

            "unmapped_terms":
                list(
                    set(
                        unmapped_from_reconciler
                        + unmapped
                    )
                )[:20],

            "processing_notes":
                notes
        }


    def _safe_llm(
        self,
        text,
        source_type,
        source_ref,
        known_skills
    ):
        """
        Run LLM interpretation safely.

        Only keep evidence whose source excerpt
        appears verbatim in the original input.
        """

        items = self.llm.interpret(
            text,
            source_type,
            source_ref,
            known_skills
        )

        valid_items = []

        for item in items:

            excerpt = item.get(
                "source_excerpt",
                ""
            )

            # No evidence excerpt = reject
            if not excerpt:
                continue

            # Hallucinated/paraphrased excerpt = reject
            if excerpt not in text:
                continue

            valid_items.append(item)

        return valid_items

    def _iter_sources(self, profile):
        """
        Convert all supported freelancer material
        into text sources.
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
                f"Language: "
                f"{sample.get('language', '')}. "
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
                work.get(
                    "description",
                    ""
                ),
                "work_description",
                work["work_id"]
            )