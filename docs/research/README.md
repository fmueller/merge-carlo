# Research notes

This folder records the literature review behind the v0.2.0 quality-adjusted
workflow proposal. The notes are an engineering synthesis, not a systematic
review or a claim that the cited results generalize to every repository.

## Reading order

1. [Defect rate and defect prediction](defect-rate-and-prediction.md)
2. [Agentic engineering and AI coding quality](agentic-engineering-and-quality.md)
3. [References and study notes](references.md)

## Use in merge-carlo

The research supports using changed-code size as an exposure measure alongside
relative churn, task type, CI/test evidence, review behavior, and repository-
specific baselines. It does not support a universal defects-per-line constant,
a fixed AI defect multiplier, or an individual contributor quality score.

The current v0.2.0 specification therefore starts with a quality evidence and
data contract. Descriptive signals must remain separate from confirmed defects,
and observational associations must not be presented as intervention effects.

## Attribution and permitted use

These files contain bibliographic metadata, links, and original summaries. They
do not reproduce paper text, tables, figures, PDFs, supplementary material, or
datasets. Publisher and repository links are provided for readers to access the
authoritative versions under their own terms. Several cited papers are openly
available through ACM or arXiv; where a publisher page is not open access, the
notes link only to the citation or an author-provided preprint.

This citation-and-summary approach avoids redistributing copyrighted material
while preserving author, venue, DOI, and URL attribution. It is a documentation
practice, not legal advice; publisher terms govern any later reuse of the source
material.

Research checked: 2026-09-17.
