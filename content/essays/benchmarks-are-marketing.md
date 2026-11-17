---
title: "Benchmarks Are Marketing Until Someone Else Runs Them"
slug: benchmarks-are-marketing
date: 2026-11-16
topic: ai
summary: "A company's own AI benchmark scores are advertising until an independent party checks them, and independence itself comes in degrees. What credible evaluation requires, and how readers can tell the difference in five minutes."
hero_image: /media/benchmarks-are-marketing/hero.webp
hero_alt: "A scoreboard whose numbers are partly covered by a hand, suggesting results shown without the conditions that produced them."
draft: false
---

On April 5, 2025, Meta released two Llama 4 models and [led with a number](https://ai.meta.com/blog/llama-4-multimodal-intelligence/): an Arena score of 1,417 for Maverick, which Meta described as Elo, on LMArena, the crowd-voted chatbot leaderboard. That put it second overall, above GPT-4o and just behind Gemini 2.5 Pro. The score was real. It was also earned by a different model from the one Meta shipped. The announcement acknowledged that the LMArena entry was an “experimental chat version,” tuned for conversationality.

LMArena [said afterward](https://x.com/lmarena_ai/status/1909397817434816562) that Meta’s interpretation of its policy did not match what it expects from providers, and that Meta should have made clear the entry was customized to optimize for human preference. Once the release version was scored, it landed around 32nd place, according to [The Decoder’s April 12 update](https://the-decoder.com/metas-llama-4-models-show-promise-on-standard-tests-but-struggle-with-long-context-tasks/). The same report said that with style control switched on, which tries to adjust for formatting and tone, the experimental model fell from second to fifth.

Notice what Meta did not do. It did not invent a number. It disclosed the variant, in small type. Marketing rarely needs a lie. It needs only a choice about which true thing goes in the headline.

That is why a line that keeps turning up in weekly AI roundups, that many performance claims come from company-run tests, deserves more than a shrug. A company-run test is not fraud. It is advertising: a claim by a party with a stake in the answer, unverified until someone independent of the vendor checks it. My argument has two halves. First, “someone else ran it” is necessary but not sufficient, because evaluators have interests, benchmarks have bugs, and scoring harnesses can be gamed. Second, credible evaluation has recognizable features, and a reader can check most of them without a PhD.

## The four dials behind every vendor chart

Every headline score is the product of choices that rarely make it into the chart: which model, how much compute, how many attempts, and what it is compared against.

**Model.** The vendor decides which variant gets tested. Maverick is the example above: the entry that won votes was not the one people could download.

**Compute.** In December 2024, OpenAI said o3 could solve more than 25 percent of FrontierMath, a set of research-level problems, while rival models managed under 2 percent. That figure came from what OpenAI’s chief research officer described as aggressive test-time compute settings. When Epoch AI, which maintains the benchmark, [ran the public o3 in April 2025](https://dataconomy.com/2025/04/21/openais-o3-claimed-25-percent-independent-test-says-try-10), it measured about 10 percent. Epoch said the gap could reflect a more powerful internal scaffold, more test-time compute, or a different problem subset, and noted it had used an updated version of the benchmark. OpenAI’s own published results included a lower-bound score consistent with Epoch’s figure, and the ARC Prize Foundation, which had tested a pre-release o3, said the shipped model was tuned for chat and product use with smaller compute tiers. The 25 percent was not fabricated. It described a configuration customers could not buy.

**Attempts.** In February 2025, xAI published an AIME 2025 chart showing two Grok 3 variants ahead of OpenAI’s o3-mini-high. OpenAI staff pointed out that the chart [left out o3-mini-high’s score at “cons@64,”](https://techcrunch.com/2025/02/22/did-xai-lie-about-grok-3s-benchmarks) where a model gets 64 tries per problem and the most common answer counts. On first-attempt scoring, TechCrunch reported, both Grok 3 variants fell below o3-mini-high. xAI co-founder Igor Babuschkin defended the chart. The fight was over which comparison was fair, which is exactly the kind of choice a vendor makes alone.

**Comparison.** Which benchmarks and rivals appear is also chosen. DeepSeek’s own materials put DeepSeek V4 Pro about on par with Claude Opus 4.6 and GPT-5.4. NIST’s Center for AI Standards and Innovation (CAISI), which says it [pre-committed to its benchmark suite](https://www.nist.gov/news-events/news/2026/05/caisi-evaluation-deepseek-v4-pro) rather than picking benchmarks after seeing results, measured the model nearer GPT-5, about eight months behind the frontier.

None of this requires dishonesty. Each choice is defensible somewhere, and each leaves the reader unable to tell whether two bars were produced under the same conditions.

## “Independent” comes in degrees

Outside evaluation fixes part of this. Epoch’s re-run is what exposed the o3 gap. But independence has grades, and the history is instructive.

FrontierMath was commissioned by OpenAI, which owns the problems. [Epoch’s own clarification](https://epoch.ai/latest/openai-and-frontiermath) says OpenAI has access to the statements and solutions except for a 50-question holdout set that was still being finalized. Epoch disclosed the funding on December 20, 2024, after o3’s unveiling, and said its contract had barred earlier disclosure. Its associate director later [acknowledged a mistake](https://techcrunch.com/2025/01/19/ai-benchmarking-organization-criticized-for-waiting-to-disclose-funding-from-openai) in not being more transparent, and its lead mathematician said Epoch [could not vouch for OpenAI’s internal score](https://the-decoder.com/openai-quietly-funded-independent-math-benchmark-before-setting-record-with-o3/) until the holdout was ready. Months later Epoch published the unflattering 10 percent. Both facts are true: the relationship was real and disclosed too late, and the evaluator still reported a number its funder would not have chosen.

LMArena is the larger case. A 2025 audit, [*The Leaderboard Illusion*](https://arxiv.org/abs/2504.20879), examined roughly two million battles covering 243 models from 42 providers. It found an undisclosed policy that let a handful of providers privately test many variants and publish only the best; Meta tested 27 in a single month before Llama 4. Identical checkpoints of one model, submitted separately, scored 1,069 and 1,052, a measure of how much noise a leaderboard carries. The paper also estimated that Google and OpenAI each received about a fifth of all arena data. In January 2026, LMArena [raised $150 million at a $1.7 billion valuation](https://techcrunch.com/2026/01/06/lmarena-lands-1.7b-valuation-four-months-after-launching-its-product/). Its [announcement](https://www.prnewswire.com/news-releases/lmarena-raises-150-million-to-build-the-worlds-most-trusted-ai-evaluation-platform-302653012.html) described working with labs and enterprises including OpenAI, Google and xAI and, separately, earning revenue from paid evaluation services for labs and enterprises. Which partners pay for what is not spelled out. A company that ranks models while selling services to the companies that build them has a potential conflict, and the remedy is disclosure and safeguards, which is what the audit asked for.

Government evaluation faces the same questions. CAISI’s DeepSeek work has real strengths: it covered nine benchmarks across five domains, reproduced DeepSeek’s own GPQA-Diamond result to rule out configuration errors, and noted that its SWE-bench Verified scores run lower than other evaluators’, likely because of scaffold and token-budget differences. It also has limits. Two of its benchmarks are held out: ARC-AGI-2’s semi-private set, which may have been exposed to limited third parties, and PortBench, CAISI’s own non-public software test, whose description CAISI says will come later. Outsiders cannot audit what they cannot see. For cost comparisons, CAISI filtered the U.S. field down to one reference model, GPT-5.4 mini, a choice it disclosed and that [critics have questioned](https://decrypt.co/366685/us-says-china-best-ai-models-lag-behind-experts-not-sure).

Stanford’s [2026 AI Index](https://hai.stanford.edu/ai-index/2026-ai-index-report), meanwhile, put the U.S.–China performance gap at 2.7 percent. That figure compares the top U.S. and top Chinese models on the Arena leaderboard in March 2026, Claude Opus 4.6 against ByteDance’s Dola-Seed-2.0 Preview. It does not measure DeepSeek V4 Pro on CAISI’s suite. The two numbers use different models, methods and comparison populations, so neither refutes the other. An independent number is another claim. It should be asked the same questions as the first.

## When the benchmark itself breaks

SWE-bench Verified was the coding benchmark of its era. OpenAI helped create it in August 2024, and it became a fixture of frontier launch posts. On February 23, 2026, [OpenAI said it had stopped reporting it](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/). Its audit covered 138 problems that o3 did not consistently solve, each reviewed by at least six engineers. Of those, 59.4 percent had material problems in test design or problem description: 35.5 percent had tests so narrow they rejected functionally correct solutions, 18.8 percent had tests checking functionality the description never asked for, and 5.1 percent had other defects. Separately, when OpenAI probed GPT-5.2, Claude Opus 4.5 and Gemini 3 Flash Preview, each could reproduce original human-written fixes or verbatim problem details for some tasks, which means the models had seen them in training. OpenAI concluded that recent gains increasingly reflect exposure to the benchmark rather than better engineering.

Epoch’s [September 2026 review](https://epoch.ai/benchmarks/swe-bench-verified/review) rated the benchmark “Flawed,” noting that even OpenAI’s limited sample implies a floor of 16.4 percent of the full set being broken. The replacement OpenAI recommended, SWE-bench Pro, has drawn scrutiny too: a September 2026 paper, [*SWE-Bench Pro Verified*](https://arxiv.org/pdf/2609.08149), set out to repair broken instances after external audits.

Contamination is one failure. The harness is another. In April 2026, [Berkeley researchers](https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/) built an automated agent that audited eight agent benchmarks and found every one could be exploited to near-perfect scores without solving a task: 100 percent on Terminal-Bench, SWE-bench Verified, SWE-bench Pro, FieldWorkArena and CAR-bench, about 100 percent on WebArena, about 98 percent on GAIA and 73 percent on OSWorld ([paper](https://arxiv.org/abs/2605.12673)). A ten-line pytest configuration file was enough to make every SWE-bench Verified instance count as resolved. On FieldWorkArena, sending `{}` as the answer passed all 890 tasks, because the validator checked only that the last message came from the assistant, not whether the answer was correct. The authors say plainly that they are not claiming current leaders cheated. A score is only as trustworthy as the wall between the agent and the grader.

Zoom out and the problem is the measure itself. An [Oxford-led review](https://arxiv.org/abs/2511.04703) of 445 benchmarks from leading conferences, with 29 expert reviewers, found patterns in the phenomena, tasks and metrics that undermine the validity of the claims made from them. Fewer than one in ten benchmarks used complete real-world tasks. A benchmark can be clean, uncontaminated and correctly graded and still not measure what the press release says it measures.

## What credible evaluation looks like

The properties are not mysterious.

**It is configured in the open.** Model version, number of attempts, sampling settings, token and time limits, tool access and scaffold should all be stated. Epoch’s benchmark-review rubric makes this the first gate: if tasks, scoring logic and harness settings cannot be inspected, even privately by reviewers under NDA, the benchmark cannot be rated at all. CAISI’s reproduction of DeepSeek’s own GPQA-Diamond number is the practical version: confirm your setup can match the vendor’s before claiming it cannot match the vendor’s other results.

**It tests what the vendor could not tune for.** Public, static test sets leak into training data, as the SWE-bench record shows. Credible evaluators hold part of the test out, rotate it, and commit to the suite before seeing results. Privacy has a cost, because outsiders cannot check what they cannot see; the workable compromise is audit by cleared third parties. A private benchmark nobody trustworthy has inspected is another way of saying “trust us.”

**It reports uncertainty.** Epoch’s rubric recommends at least five runs per model so error bars exist, and CAISI reports 95 percent confidence intervals on its aggregate scores. The identical checkpoints that scored 17 points apart on LMArena show why. A two-point lead with no interval is a rumor.

**It audits the grader and isolates the agent.** Epoch labels a benchmark “Flawed” when scoring errors could affect 20 percent or more of the total score, and it samples tasks to find out. Berkeley adds a second requirement: the system under test must not be able to edit its own exam.

**It measures the claimed thing.** The Oxford review’s central point is construct validity. A “reasoning” score built from multiple-choice trivia supports a much narrower claim than the one in the headline.

**Its evaluator is accountable.** Funding and commercial ties should be disclosed at publication, not after a controversy. Private-testing rules should be public, and unflattering runs should not be quietly withdrawn. The Leaderboard Illusion authors recommend limits on private testing, an end to score retraction, and fair sampling and deprecation policies.

**It admits when its number has expired.** METR’s [2025 randomized trial](https://arxiv.org/abs/2507.09089) is the model. Sixteen experienced open-source developers worked on 246 real tasks from their own repositories, with AI tools allowed or banned at random. They forecast a 24 percent speedup and afterward believed they had gained about 20 percent, yet measured completion time rose 19 percent. That is evidence about real work, which benchmarks rarely provide. Then came the part that matters most for trust. In [February 2026](https://metr.org/blog/2026-02-24-uplift-update/), METR reported that selection effects were undermining its follow-up: developers were increasingly unwilling to work without AI or to submit tasks where AI would help most. It said its new data was “only very weak evidence” for the size of any speedup, with an estimate for returning developers whose interval ran from a 38 percent reduction in task time to a 9 percent increase, and it began redesigning the experiment. The original study was small and the tools have since changed. That is the point: an evaluator that says its own number has gone stale is behaving differently from one that lets the old figure circulate.

## A five-minute check

When a launch post or roundup hands you a number, ask:

1. **Which exact model, and can I use it?** A custom variant, pre-release checkpoint or maximum-compute mode is not the product on offer.
2. **How many tries, how much compute, which scaffold?** Look for “cons@64,” “with tools” or “best of N,” and check that rivals were measured the same way.
3. **Who ran it, who paid, who saw the questions?** “Independent” should come with a funding disclosure.
4. **Is there an interval, and does the lead exceed it?** No run count or error bar means assume the margin is noise.
5. **How old and how public is the test?** Old public benchmarks should be presumed contaminated; fresher, held-out sets deserve more weight if someone credible has audited them.
6. **Has anyone reproduced it in a different harness?** Trackers such as Epoch, Artificial Analysis and Vals AI, and government bodies such as CAISI and the UK’s AI Security Institute, are worth checking. When vendor and outsider disagree, read both methodologies instead of siding with the one you prefer.

A seventh test no leaderboard can run for you: take twenty or thirty tasks from your own work and try the model on them.

## The fair objection

Company-run evaluations are not worthless, and calling them marketing is not meant as an insult. Labs need internal evals to track regressions and decide what to ship, and for unreleased models they are often the only evidence that exists. Outside evaluators are slower, smaller, fragmented across competing leaderboards, and blind to anything that has not shipped. Vendors also sometimes tell hard truths first: OpenAI’s decision to retire a benchmark it helped build deserves credit. Even that came with a wrinkle, though. [The Decoder noted](https://the-decoder.com/openai-wants-to-retire-the-ai-coding-benchmark-that-everyone-has-been-competing-on/) a possible strategic angle, since a contaminated benchmark can flatter rivals, especially open-weight ones, and retiring it removes that flattery. Incentives bend even confessions.

So “marketing” is better read as a category than a charge: a claim made by a party with a stake. Marketing can be accurate. It has not yet earned the word “evidence,” and the burden of earning it falls on the party making the claim, not on the reader.

## The rule

An evaluation becomes stronger evidence when the evaluator operates independently of the vendor’s control, discloses its interests, applies a protocol fixed in advance consistently across models, and publishes its methodology and uncertainty for others to check. Few results meet all of that. Many meet some. Weight claims accordingly, treat independent numbers as claims that also need checking, and when the stakes are your money or your product, run the test yourself.

## Sources

Primary sources first.

- Meta, Llama 4 announcement: https://ai.meta.com/blog/llama-4-multimodal-intelligence/
- LMArena statement on Llama 4 Maverick: https://x.com/lmarena_ai/status/1909397817434816562
- Singh et al., *The Leaderboard Illusion*: https://arxiv.org/abs/2504.20879
- NIST CAISI, Evaluation of DeepSeek V4 Pro: https://www.nist.gov/news-events/news/2026/05/caisi-evaluation-deepseek-v4-pro
- Epoch AI, clarification on OpenAI and FrontierMath: https://epoch.ai/latest/openai-and-frontiermath
- OpenAI, why it stopped reporting SWE-bench Verified: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- Epoch AI, SWE-bench Verified benchmark review: https://epoch.ai/benchmarks/swe-bench-verified/review
- Berkeley RDI, How We Broke Top AI Agent Benchmarks: https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/ and paper https://arxiv.org/abs/2605.12673
- Bean et al., *Measuring what Matters* (Oxford): https://arxiv.org/abs/2511.04703
- METR, 2025 trial: https://arxiv.org/abs/2507.09089
- METR, 2026 experiment redesign: https://metr.org/blog/2026-02-24-uplift-update/
- Stanford HAI, 2026 AI Index: https://hai.stanford.edu/ai-index/2026-ai-index-report
- *SWE-Bench Pro Verified*: https://arxiv.org/pdf/2609.08149

Secondary reporting:

- The Decoder, Llama 4 and LMArena update: https://the-decoder.com/metas-llama-4-models-show-promise-on-standard-tests-but-struggle-with-long-context-tasks/
- TechCrunch, Grok 3 AIME chart: https://techcrunch.com/2025/02/22/did-xai-lie-about-grok-3s-benchmarks
- Dataconomy, o3 FrontierMath gap: https://dataconomy.com/2025/04/21/openais-o3-claimed-25-percent-independent-test-says-try-10
- TechCrunch, Epoch funding disclosure: https://techcrunch.com/2025/01/19/ai-benchmarking-organization-criticized-for-waiting-to-disclose-funding-from-openai
- The Decoder, FrontierMath funding: https://the-decoder.com/openai-quietly-funded-independent-math-benchmark-before-setting-record-with-o3/
- TechCrunch, LMArena valuation: https://techcrunch.com/2026/01/06/lmarena-lands-1.7b-valuation-four-months-after-launching-its-product/
- LMArena funding announcement: https://www.prnewswire.com/news-releases/lmarena-raises-150-million-to-build-the-worlds-most-trusted-ai-evaluation-platform-302653012.html
- Decrypt, critics of the CAISI evaluation: https://decrypt.co/366685/us-says-china-best-ai-models-lag-behind-experts-not-sure
- The Decoder, OpenAI and SWE-bench Verified: https://the-decoder.com/openai-wants-to-retire-the-ai-coding-benchmark-that-everyone-has-been-competing-on/
