"""Service layer — business rules distilled from the policy documents.

Services are the deterministic brain of the platform. They compute SLAs,
cancellation fees, and service-credit eligibility from structured data +
policy constants, returning fully-explained, citation-bearing results. The LLM
never computes these numbers — it only narrates the verified output, which is
what makes the platform's answers trustworthy and hallucination-resistant.
"""
