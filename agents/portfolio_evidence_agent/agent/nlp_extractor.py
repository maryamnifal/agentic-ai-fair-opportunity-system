import json
import spacy
from spacy.matcher import PhraseMatcher


class NLPExtractor:

    def __init__(self, taxonomy_path="data/skill_taxonomy.json"):

        # Load spaCy model
        self.nlp = spacy.load("en_core_web_md")

        # Load skill taxonomy
        with open(taxonomy_path, "r", encoding="utf-8") as file:
            self.taxonomy = json.load(file)

        # Create PhraseMatcher
        self.matcher = PhraseMatcher(
            self.nlp.vocab,
            attr="LOWER"
        )

        # Add skills and aliases
        for canonical_skill, details in self.taxonomy.items():

            terms = [
                canonical_skill
            ]

            terms.extend(
                details.get("aliases", [])
            )

            patterns = [
                self.nlp.make_doc(term)
                for term in terms
            ]

            self.matcher.add(
                canonical_skill,
                patterns
            )


    def extract(self, text, source_type, source_ref):

        """
        Extract explicit skills from text.
        """

        doc = self.nlp(text)

        matches = self.matcher(doc)

        results = []

        seen = set()


        for match_id, start, end in matches:

            skill = self.nlp.vocab.strings[match_id]


            # Avoid duplicate skills
            if skill in seen:
                continue

            seen.add(skill)


            span = doc[start:end]


            results.append({

                "skill": skill,

                "skill_category":
                    self.taxonomy[skill]["category"],

                "source_type":
                    source_type,

                "source_ref":
                    source_ref,

                "source_excerpt":
                    self._create_excerpt(
                        doc,
                        start,
                        end
                    ),

                "extraction_method":
                    "ner",

                "confidence":
                    0.95,

                "reasoning":
                    f"Explicit mention of {span.text} in {source_type}."

            })


        return results



    def _create_excerpt(
            self,
            doc,
            start,
            end,
            window=8
    ):

        """
        Capture surrounding words for explainability.
        """

        start_index = max(
            0,
            start - window
        )

        end_index = min(
            len(doc),
            end + window
        )


        return doc[start_index:end_index].text.strip()