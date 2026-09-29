# Sanity Context + Knowledge Base setup

For the strongest Path One demo, use two Context surfaces:

1. **GROQ mode** for exact structured farm state/policy queries.
2. **Knowledge Base mode** for broader agronomy notes, extension guidance, and source documents.

Keep the structured operating rules in the dataset. Put longer source material into a Sanity Knowledge Base and attach that KB to a second Context MCP endpoint.

## Suggested Knowledge Base material

- crop extension notes
- irrigation best-practice documents
- market-risk methodology
- farm safety notes
- agronomy references

The agent should use the structured dataset for exact thresholds and the Knowledge Base for supporting explanations and source context.

## Judge-friendly test

Ask a question that requires both:

"Given the current wheat moisture and market demand, should the farm water first or sell first? Explain the policy threshold and the agronomic rationale."

A strong trace should show:

- structured query for current farm policy/crop rule
- Knowledge Base retrieval for supporting agronomy context
- final recommendation that distinguishes hard constraints from contextual evidence

Do not put secrets in the Knowledge Base or public dataset.
