# References and study notes

These are the papers cited by the research notes in this folder. The summaries
are original notes; consult the linked source for the authoritative text,
methods, data, and qualifications.

## Defect prediction and code metrics

1. Nachiappan Nagappan and Thomas Ball. 2005. “Use of relative code churn
   measures to predict system defect density.” ICSE. DOI:
   <https://doi.org/10.1145/1062455.1062514>.
2. Jalaj Pachouly, Swati Ahirrao, Ketan Kotecha, Ganeshsree Selvachandran,
   and Ajith Abraham. 2022. “A systematic literature review on software defect
   prediction using artificial intelligence: Datasets, Data Validation
   Methods, Approaches, and Tools.” *Engineering Applications of Artificial
   Intelligence* 111, 104773. DOI:
   <https://doi.org/10.1016/j.engappai.2022.104773>.
3. Peng He, Bing Li, Xiao Liu, Jun Chen, and Yutao Ma. 2015. “An empirical
   study on software defect prediction with a simplified metric set.”
   *Information and Software Technology* 59, 170–190. DOI:
   <https://doi.org/10.1016/j.infsof.2014.11.006>. Preprint:
   <https://arxiv.org/abs/1402.3873>.

## AI-generated code and security

4. Yujia Fu, Peng Liang, Amjed Tahir, Zengyang Li, Mojtaba Shahin, Jiaxin Yu,
   and Jinfu Chen. 2025. “Security Weaknesses of Copilot-Generated Code in
   GitHub Projects: An Empirical Study.” *ACM Transactions on Software
   Engineering and Methodology*. DOI: <https://doi.org/10.1145/3716848>.
   Author preprint: <https://arxiv.org/abs/2310.02059>.
5. Cristina Improta et al. 2025. “Human-Written vs. AI-Generated Code: A
   Large-Scale Study of Defects, Vulnerabilities, and Complexity.” arXiv:
   <https://arxiv.org/abs/2508.21634>.

## Agent-authored pull requests and repository outcomes

6. Miku Watanabe, Hao Li, Yutaro Kashiwa, Brittany Reid, Hajimu Iida, and
   Ahmed E. Hassan. 2025. “On the Use of Agentic Coding: An Empirical Study of
   Pull Requests on GitHub.” arXiv: <https://arxiv.org/abs/2509.14745>.
7. Pat Rondon, Renyao Wei, José Cambronero, Jürgen Cito, Aaron Sun, Siddhant
   Sanyam, Michele Tufano, and Satish Chandra. 2025. “Evaluating Agent-Based
   Program Repair at Google.” ICSE-SEIP. DOI:
   <https://doi.org/10.1109/ICSE-SEIP66354.2025.00038>. Preprint:
   <https://arxiv.org/abs/2501.07531>.
8. Ira Ceka, Saurabh Pujar, Shyam Ramji, Luca Buratti, Gail Kaiser, and
   Baishakhi Ray. 2025. “Understanding Automated Program Repair Agents Through
   the Lens of Traceability: An Empirical Study.” arXiv:
   <https://arxiv.org/abs/2506.08311>.
9. Worawalan Chatlatanagulchai et al. 2025. “Agent READMEs: An Empirical Study
   of Context Files for Agentic Coding.” arXiv:
   <https://arxiv.org/abs/2511.12884>.
10. “SWE-EVO: Benchmarking Coding Agents in Long-Horizon Software Evolution
    Scenarios.” 2025. arXiv: <https://arxiv.org/abs/2512.18470>.
11. Daniel Ogenrwot and John Businge. 2026. “How AI Coding Agents Modify Code:
    A Large-Scale Study of GitHub Pull Requests.” MSR. DOI:
    <https://doi.org/10.1145/3793302.3793603>. Preprint:
    <https://arxiv.org/abs/2601.17581>.
12. Ramtin Ehsani, Sakshi Pathak, Shriya Rawal, Abdullah Al Mujahid, Mia
    Mohammad Imran, and Preetha Chatterjee. 2026. “Where Do AI Coding Agents
    Fail? An Empirical Study of Failed Agentic Pull Requests in GitHub.” MSR.
    DOI: <https://doi.org/10.1145/3793302.3793579>. Open-access source:
    <https://dl.acm.org/doi/full/10.1145/3793302.3793579>.
13. Shamse Tasnim Cynthia, Al Muttakin, and Banani Roy. 2026. “Beyond Bug
    Fixes: An Empirical Investigation of Post-Merge Code Quality Issues in
    Agent-Generated Pull Requests.” MSR. DOI:
    <https://doi.org/10.1145/3793302.3793615>. Preprint:
    <https://arxiv.org/abs/2601.20109>.
14. “Behind Agentic Pull Requests: An Empirical Study on Developer
    Interventions in AI Agent-Authored Pull Requests.” 2026. MSR. DOI:
    <https://doi.org/10.1145/3793302.3793586>.

## Controlled productivity evidence

15. “How Much Does AI Impact Development Speed? An Enterprise-Based Randomized
    Controlled Trial.” 2025. ICSE-SEIP. Preprint:
    <https://arxiv.org/abs/2410.12944>.
16. Joel Becker, Nate Rush, Beth Barnes, and David Rein. 2025. “Measuring the
    Impact of Early-2025 AI on Experienced Open-Source Developer Productivity.”
    arXiv: <https://arxiv.org/abs/2507.09089>. Study update and qualifications:
    <https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study>.

## Scope note

These sources mix industrial studies, repository mining, controlled
experiments, benchmarks, and preprints. Their outcomes are not interchangeable:
static findings, test-passing patches, merge outcomes, review effort, and
production incidents answer different questions. That heterogeneity is itself
part of the rationale for the v0.2.0 evidence-tier and provenance requirements.
