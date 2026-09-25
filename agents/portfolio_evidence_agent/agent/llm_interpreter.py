import json
import os

import torch
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer


load_dotenv()


SYSTEM_PROMPT = """
You are the contextual skill interpretation layer of a freelancer
portfolio evidence system.

Your task is to identify ALL technical skills that are supported by
the supplied portfolio text.

There are two kinds of evidence:

1. EXPLICIT EVIDENCE
   The skill name appears directly in the text.

2. STRONGLY IMPLIED EVIDENCE
   The skill is not named directly, but the activity or technology
   described provides clear evidence of that skill.

IMPORTANT:
Do not stop after finding explicit skills.
After finding explicit skills, examine the text again for strongly
implied skills.

Use the supplied known skill vocabulary whenever possible.

Examples:

Input:
"Built server-side APIs with Django."

Supported skills:
- Django
  Reason: Django is explicitly named.

- Python
  Reason: Django is a Python web framework, so using Django strongly
  supports Python usage.

- REST API
  Reason: Building server-side APIs in this context provides evidence
  of API development and REST API is the relevant canonical skill in
  the supplied vocabulary.

Do NOT infer unrelated technologies such as PostgreSQL, Docker or AWS
unless the text actually supports them.

Rules:

- Return every explicit or strongly implied skill supported by the text.
- Do not invent unrelated skills.
- Do not infer from a project title alone.
- Prefer canonical names from the known skill vocabulary.
- Explicit evidence: confidence normally 0.90 to 0.98.
- Strong implication: confidence normally 0.70 to 0.85.
- Weak evidence should not be returned.
- Do not return confidence below 0.50.
- source_excerpt MUST be copied verbatim from the provided input text.
- For an implied skill, the excerpt does not need to contain the skill
  name itself; it must contain the text that supports the inference.
- Give one short reasoning sentence for each skill.
- Return ONLY a JSON array.
- Do not use markdown.
- Do not write anything before or after the JSON.
- The examples above are instructions only. Never use facts, technologies,
    or skills from an example as evidence for the current portfolio text.
    Only the current portfolio text is evidence.

Output format:

[
    {
        "skill": "Skill Name",
        "source_excerpt": "exact substring from input text",
        "confidence": 0.80,
        "reasoning": "Short explanation of why the text supports this skill."
    }
]
"""


class LLMInterpreter:

    def __init__(self):

        self.model_name = os.getenv(
            "LLM_MODEL",
            "Qwen/Qwen2.5-1.5B-Instruct"
        )

        self.tokenizer = None
        self.model = None


    def _load_model(self):
        """
        Load the Hugging Face model only when it is first needed.

        This avoids loading a large model when running
        NLP-only tests.
        """

        if self.model is not None:
            return

        print(
            f"[LLM] Loading local model: "
            f"{self.model_name}"
        )

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype="auto",
            device_map="auto"
        )

        self.model.eval()


    def interpret(
        self,
        text,
        source_type,
        source_ref,
        known_skills
    ):
        """
        Identify contextual or implied technical skills
        using a local Hugging Face instruct model.
        """

        try:

            self._load_model()

            user_prompt = (
                "Known skill vocabulary:\n"
                f"{', '.join(known_skills)}\n\n"
                f"Portfolio text ({source_type}):\n"
                f'"""{text}"""\n\n'
                "Identify ALL supported skills. "
                "First identify explicit skills, then perform a second pass "
                "for strongly implied skills. "
                "Return only the JSON array."
            )

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]

            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

            inputs = self.tokenizer(
                prompt,
                return_tensors="pt"
            )

            inputs = {
                key: value.to(self.model.device)
                for key, value in inputs.items()
            }


            with torch.no_grad():

                output = self.model.generate(
                    **inputs,
                    max_new_tokens=600,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id
                )


            # Decode only newly generated tokens
            generated_tokens = output[
                0,
                inputs["input_ids"].shape[1]:
            ]

            raw = self.tokenizer.decode(
                generated_tokens,
                skip_special_tokens=True
            ).strip()


            # Remove accidental markdown formatting
            raw = (
                raw
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )


            # Extract JSON array if the model adds extra text
            start = raw.find("[")
            end = raw.rfind("]")

            if start == -1 or end == -1:
                return []

            raw = raw[start:end + 1]

            items = json.loads(raw)


            if not isinstance(items, list):
                return []


        except json.JSONDecodeError:

            return []


        except Exception as error:

            print(
                f"[LLM] local model failed for "
                f"{source_ref}: {error}"
            )

            return []


        results = []


        for item in items:

            if not isinstance(item, dict):
                continue


            skill = item.get("skill")

            if not skill:
                continue


            try:

                confidence = float(
                    item.get(
                        "confidence",
                        0.6
                    )
                )

            except (TypeError, ValueError):

                confidence = 0.6


            confidence = max(
                0.5,
                min(
                    confidence,
                    1.0
                )
            )

            # If the skill name itself does not appear in the evidence text,
            # treat it as implied evidence and cap confidence at 0.85.
            excerpt = item.get(
                "source_excerpt",
                ""
            )

            if skill.lower() not in excerpt.lower():
                confidence = min(
                    confidence,
                    0.85
                )


            results.append(
                {
                    "skill":
                        skill,

                    "skill_category":
                        "uncategorised",

                    "source_type":
                        source_type,

                    "source_ref":
                        source_ref,

                    "source_excerpt":
                         excerpt[:300],

                    "extraction_method":
                        "llm",

                    "confidence":
                        confidence,

                    "reasoning":
                        item.get(
                            "reasoning",
                            "Inferred by local LLM."
                        )
                }
            )


        return results