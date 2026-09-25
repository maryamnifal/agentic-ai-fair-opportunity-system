class Reconciler:

    def __init__(self, taxonomy):
        self.taxonomy = taxonomy

        # Build alias → canonical skill lookup
        self.alias_map = {}

        for canonical, details in taxonomy.items():

            self.alias_map[canonical.lower()] = canonical

            for alias in details.get("aliases", []):
                self.alias_map[alias.lower()] = canonical


    def canonicalise(self, skill):
        """
        Convert a skill or alias into its canonical taxonomy name.

        Example:
        postgres -> PostgreSQL
        psql -> PostgreSQL
        django -> Django
        """

        if not skill:
            return None

        return self.alias_map.get(
            skill.lower().strip()
        )


    def merge(self, ner_items, llm_items):
        """
        Merge NLP and LLM evidence into one clean evidence list.
        """

        merged = {}
        unmapped = []

        all_items = ner_items + llm_items


        for item in all_items:

            canonical = self.canonicalise(
                item["skill"]
            )


            # Skill not present in taxonomy
            if canonical is None:
                unmapped.append(
                    item["skill"]
                )
                continue


            # Replace raw skill name with canonical name
            item["skill"] = canonical

            item["skill_category"] = (
                self.taxonomy[canonical]["category"]
            )


            # One evidence item per skill per source
            key = (
                canonical,
                item["source_ref"]
            )


            if key not in merged:

                merged[key] = item


            else:

                existing = merged[key]


                # NLP and LLM both found same skill
                if (
                    existing["extraction_method"]
                    != item["extraction_method"]
                ):

                    existing["extraction_method"] = "both"

                    existing["confidence"] = min(
                        0.98,
                        max(
                            existing["confidence"],
                            item["confidence"]
                        ) + 0.05
                    )

                    existing["reasoning"] = (
                        "Confirmed by both rule-based extraction "
                        "and LLM interpretation."
                    )


                else:

                    # Same method found duplicate
                    existing["confidence"] = max(
                        existing["confidence"],
                        item["confidence"]
                    )


        items = list(
            merged.values()
        )


        # Add evidence IDs
        for index, item in enumerate(
            items,
            start=1
        ):

            item["evidence_id"] = (
                f"ev_{index:03d}"
            )


        return items, list(
            set(unmapped)
        )