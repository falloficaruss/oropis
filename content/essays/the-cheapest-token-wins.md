---
title: "The Cheapest Token Wins: The New Economics of AI"
slug: the-cheapest-token-wins
date: 2026-11-16
topic: ai
summary: "AI’s next competitive advantage may come less from building ever-larger models than from delivering useful intelligence efficiently. But the economics of inference are colliding with a harder constraint: the electricity, land and public consent required to power the industry’s expansion."
hero_image: /media/the-cheapest-token-wins/hero.webp
hero_alt: "A vast AI data centre at dusk, with illuminated server racks visible through glass walls and high-voltage power lines stretching towards the horizon."
draft: false
---

# The Cheapest Token Wins: The New Economics of AI

*The next AI advantage may not belong to whoever builds the largest model. It may belong to whoever can turn the least computing power and electricity into the most useful work—and persuade the public to let them build the infrastructure to do it.*

The artificial intelligence industry has become accustomed to measuring progress by scale. Larger models, larger training clusters, larger chip orders and larger data-centre commitments have become the familiar markers of ambition. Every new infrastructure announcement seems to arrive with another impressive number attached to it. The implication is hard to miss: the companies that can accumulate the most compute will eventually own the future.

I think that is an incomplete way to understand where the industry is going. The next phase of competition will be shaped by two questions that are often treated separately. First, how cheaply can a company deliver intelligence that is actually useful? Second, how much electricity, land and public tolerance will be available to support the infrastructure behind that intelligence?

These are not separate problems. Inference efficiency determines how much work can be extracted from a given amount of compute. Infrastructure constraints determine whether that compute can be expanded at all. A company that understands only the first may build an excellent product it cannot afford to scale. A company that understands only the second may construct expensive capacity that its customers cannot use profitably.

The slogan “the cheapest token wins” captures part of the opportunity. But the more important measure is not the price of a token. It is the cost of completing a useful task, reliably, within an acceptable time and power budget. That is where the economics of AI are heading.

## 1. Training gets the headlines. Inference gets the bill.

Training a frontier model is an extraordinary engineering and capital project, but it is not the same economic activity as operating a product. Training is a phase of development; inference is the recurring cost of putting the model to work: answering questions, summarising documents, generating code, classifying images or taking actions through an agent.

A model can impress on a benchmark and still be a poor business choice if every interaction is expensive. A product that makes a handful of model calls in a demonstration may make millions in production. An agent that plans, searches, invokes tools and retries can consume many times the tokens of a simple chatbot. Its unit economics depend not only on model intelligence, but on how intelligently the system uses it.

This is why the falling price of inference matters so much. Stanford HAI’s *2025 AI Index* reported that the cost of querying a model at roughly GPT-3.5 performance on the MMLU benchmark fell from $20 per million tokens in November 2022 to $0.07 by October 2024, a reduction of more than 280 times. The report also found that declines varied widely by task and model. That is not proof that every production workload has become hundreds of times cheaper; benchmark equivalence and real-world service quality are not the same thing. But it is strong evidence that the cost of accessing capable language models can fall quickly ([Stanford HAI, 2025 AI Index](https://hai.stanford.edu/ai-index/2025-ai-index-report/research-and-development)).

When a key input becomes cheaper, businesses do not simply pocket the saving. They redesign products around it. Features that were too expensive to offer become viable. Products can serve more customers. Existing companies can automate more tasks. New entrants can test ideas that would previously have required a large infrastructure budget.

A lower token price is not automatically a better product. A cheap model that needs repeated retries or human repair can cost more than a larger model that gets the job right first time. The comparison must include quality, latency, reliability and the cost of failure. The objective is to minimise the cost of successfully completing work, not the invoice for generated text.

That distinction should shape how AI companies design products. The model is one component of the service, not the service itself.

## 2. The efficiency stack is becoming a competitive strategy

Quantization shows how engineering can change deployment economics. Representing model weights—and, in some methods, activations—with fewer bits can reduce memory use and data movement, allowing a model to fit on smaller hardware or serve more requests. Results depend on the model, method, hardware and workload; lower precision can also reduce quality. Treating “four-bit” as a magic setting is as simplistic as assuming the largest model is always best.

Compression is only one part of the efficiency stack. Distillation transfers useful behaviour into smaller models; continuous batching improves accelerator utilisation; speculative decoding lets a smaller draft model propose tokens for a larger model to verify. Better attention implementations, caching, kernel optimisation and context management can further reduce waste. The right combination depends on the workload.

NVIDIA’s own inference material illustrates how the industry is beginning to frame the contest. Its published comparisons for the Blackwell GB300 NVL72 system claim substantially higher token throughput per megawatt and lower cost per million tokens than its Hopper H200 comparison. Those figures are vendor- and configuration-specific, and should be read as NVIDIA’s claims rather than universal performance guarantees. Yet the metrics are revealing: tokens per second per megawatt and cost per million tokens are now central to the sales pitch ([NVIDIA inference comparisons](https://www.nvidia.com/en-us/solutions/ai/inference/)).

The shift is from measuring peak compute to measuring useful output under real serving conditions. An accelerator that sits idle, moves data inefficiently or processes oversized prompts may be a worse investment than cheaper hardware that is consistently well utilised.

Not every task belongs in a small or local model. A frontier model may justify its cost when mistakes are expensive or the task genuinely requires stronger reasoning. Efficient deployment means reserving powerful models for work that warrants them.

## 3. The compute-constrained builder may design the better system

A developer with abundant compute can afford to be careless. A developer with a modest budget must ask whether a model is needed at every stage, whether ordinary software can handle part of the task, whether retrieval can reduce context and whether a stronger model is necessary only for uncertain cases.

That pressure can produce better architecture. A document-processing agent could send every page to a frontier model for extraction, classification and explanation. Or it could parse the document first, use rules for predictable fields, apply a small model to routine cases and escalate only ambiguous ones. The second design is not always cheaper, but it gives the builder control over where expensive inference is justified.

This matters even more with agents. A ten-step workflow can multiply model usage as the system plans, searches, calls tools and checks results. A poorly designed agent may repeatedly reconsider decisions that ordinary software could handle. The advantage will come from knowing when to reason, when to act and when to stop—not from making agents “think” for longer.

As capable models become more widely available, a model API alone may become a less defensible business. Providers will still compete on reliability, speed, specialised capabilities and distribution, but application companies may capture value through workflow expertise, customer relationships, proprietary data and integration into existing operations.

Open-weight models widen deployment choices and give businesses more control over data handling and customisation. They are not automatically cheaper: hosting, maintenance, security and skilled operations all cost money. But they can reduce dependence on a single provider and let a company match a model to its constraints.

None of this means small builders have suddenly overtaken large laboratories. The largest companies retain deep advantages in hardware procurement, research, distribution, data and capital. Compute scarcity can limit experimentation as easily as it can encourage discipline. The opportunity is narrower but meaningful: a small team does not need to recreate a frontier lab to build a useful AI business. It needs to solve a valuable problem with a system whose costs make sense.

## 4. Cheaper intelligence changes who can build—and where

The beneficiaries of cheaper inference are not limited to AI startups. Small businesses can automate document processing, customer support, internal search and routine reporting without paying frontier-model prices for every step. Independent developers can test products with modest budgets. Researchers can run more experiments. Robotics teams can move selected perception and language tasks closer to the machine, where latency, connectivity and privacy may matter more than access to the largest cloud model.

Robotics makes the edge case tangible. A warehouse robot, inspection device or agricultural machine cannot assume every decision can wait for a round trip to a remote data centre. Cloud services will remain useful, but local inference can improve responsiveness and resilience. Smaller, quantized models will not make every robot autonomous; they can make it cheaper to put selected intelligence on machines operating beyond a well-connected office.

For India, the opportunity should not be defined solely as building domestic replicas of the largest American data-centre campuses. It can also come from applications designed around local cost constraints: reliable systems that work across Indian languages, run on modest hardware and automate valuable processes without chasing every general benchmark.

There are already signs of an effort to widen access to compute. The Indian government said in March 2026 that national data-centre capacity had grown from about 375 MW in 2020 to around 1,500 MW by 2025. It also reported that more than 38,000 GPUs had been onboarded through the IndiaAI compute framework, with access offered at a subsidised average rate of ₹65 per hour ([Press Information Bureau, March 13, 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2239616&lang=1&noshow=1&reg=3)). These are government-reported figures, not an independent assessment of how evenly that capacity is distributed or how much is available to each applicant. Even so, shared compute can lower the initial barrier for startups, researchers and universities.

Compute access matters only when teams can turn it into products. That requires expertise in inference servers, data pipelines, evaluation, quantization and deployment—not simply prompt writing. A cost-sensitive market can reward this engineering because customers are less likely to pay for capability they do not need.

The infrastructure challenge remains. A March 2026 parliamentary answer put India’s data-centre capacity at around 1.5 GW in 2025 and projected 13.56 GW by 2031–32—a target, not a guaranteed buildout. In August, the Ministry of Electronics and IT highlighted energy- and water-efficiency measures, including direct-to-chip liquid cooling, immersion cooling and closed-loop systems ([Ministry of Power, Rajya Sabha answer](https://sansad.in/getFile/annex/270/AU4151_DoYAWR.pdf?source=pqars); [PIB, August 12, 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2298108&lang=1&reg=1)).

India’s opportunity is to expand compute infrastructure while developing the skills and products that make each unit of compute more valuable. Data-centre capacity is not an AI strategy by itself; efficient models and workflow design could let Indian companies build competitive services without matching hyperscalers’ capital expenditure.

## 5. The electricity constraint is not a footnote

A data centre is not an abstract cloud. It is an industrial facility with a grid connection, cooling equipment, backup systems, land requirements and neighbours. Its electricity demand may be concentrated where grid capacity is already constrained; its cooling strategy can affect water use; and construction can change local land use. The effects vary by site and technology, so neither “harmless” nor “inherently damaging” is an adequate description of every facility.

The International Energy Agency’s updated outlook puts the scale of the challenge in perspective. It projects global data-centre electricity consumption to roughly double, from 485 TWh in 2025 to 950 TWh in 2030, or around 3% of global electricity demand by that point. Electricity use by AI-focused data centres is projected to grow faster, tripling over the period. The IEA also notes that bottlenecks in the supply chain and energy system are limiting the likelihood of more aggressive near-term growth scenarios ([IEA, *Key Questions on Energy and AI*](https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary%C2%A0)).

The forecast is not destiny: it depends on AI adoption, completed projects, hardware efficiency and the pace of grid expansion. But even the central projection makes data centres too large a consumer to ignore in energy planning.

Software companies work in deployment cycles measured in days or weeks. New generation, transmission lines, substations and grid connections take longer to plan, finance and build. A company can order accelerators and still find that power is unavailable at the required location or time. The constraint is no longer only whether it can afford servers, but whether the energy system can accommodate them.

Efficiency therefore matters beyond the operator’s power bill. Better utilisation can reduce the capacity needed for a workload; improved cooling can ease energy and water demand; flexible jobs can be scheduled when the grid is less constrained. Long-term power contracts and additional generation can also align expansion with supply. None removes the need for infrastructure, but each can make expansion more deliberate.

There is a catch. Cheaper inference can create more demand. When AI features become affordable, firms add them to more products and users make more requests. This rebound effect means that lower energy per token does not guarantee lower total electricity use. Efficiency can reduce the resource cost of each task while encouraging enough additional tasks to increase overall consumption. The right question is therefore not simply whether a new model is more efficient, but whether total useful output is growing faster than total resource use.

## 6. The data-centre backlash: local evidence, national interpretations

This is where AI’s infrastructure story becomes political. The November 3, 2026 US midterm elections produced a Democratic takeover of both the House and Senate. One interpretation, advanced in a November 9 commentary by the Center for European Policy Analysis, was that anger over data centres and AI infrastructure helped propel the Democratic victory. It is a plausible reading of an issue that became unusually visible during the campaign, but it should be treated as an analyst’s interpretation—not as an established explanation for the national result ([CEPA, November 9, 2026](https://cepa.org/article/midterm-fallout-ai-and-data-centers-take-center-stage/)).

Other reporting complicates the claim. The Associated Press described widespread opposition to new data centres in people’s communities and reported that restrictions passed in 44 of the 45 local elections where counting was complete. It also reported that roughly three-quarters of voters opposed a new data centre in their community. Yet the AP Voter Poll suggested that data centres were not among the most influential national voting issues: around one-quarter of voters said AI data centres were crucial to their vote for Congress, below the shares who identified the cost of living or government corruption as highly important ([Associated Press, November 6, 2026](https://abcnews.com/Technology/wireStory/data-centers-beating-midterm-elections-137902293)).

A separate Washington Post report on the results described 41 local ballot initiatives concerning data centres across 10 states, with all but one resulting in restrictions or limits. It also cited exit-poll data in which 56% of voters said AI and data centres were a major or crucial factor in their vote. That is not directly equivalent to the AP figure: “major or crucial” is a broader category than “crucial” alone, and different polls can produce different estimates ([The Washington Post, November 10, 2026](https://www.washingtonpost.com/ripple/2026/11/10/did-opposition-data-centers-fuel-blue-wave/)).

The evidence supports neither a claim that data centres decided the midterms nor that the backlash was irrelevant. Local opposition was visible and often successful, while the national result had several major drivers, including the economy, cost of living, corruption and the Iran war. A planning dispute can decide the fate of one project without being the country’s leading electoral issue.

The lesson is that people can welcome AI products and oppose a data centre near their home. Someone may use an AI assistant daily yet worry about local electricity prices, water resources or roads. They may support technological development while questioning opaque approvals or uncertainty over who pays for grid upgrades.

Reuters reported before the election that investors were watching local and state authorities because they can influence approvals, utilities and project schedules. Its analysts did not expect the backlash to derail AI investment altogether, but warned it could disrupt timing and costs ([Reuters, October 22, 2026](https://www.reuters.com/legal/transactional/investors-see-risk-us-midterms-ai-trade-data-center-backlash-builds-2026-10-22/)). A project does not need a national ban to become more expensive; a local moratorium, contested permit or unavailable grid connection can be enough.

The response needs to be practical. Developers should disclose expected electricity and water use, explain who pays for new infrastructure and make credible commitments on efficiency and community benefits. Tax revenue and construction jobs matter, but they do not answer every question. Public acceptance will not follow automatically from the promise of innovation.

## 7. Useful intelligence per megawatt

Technical ambition and physical limits now have to be considered together. A company that lowers inference cost but ignores power availability may struggle to expand. One that secures vast energy capacity but uses it inefficiently may struggle when customers demand lower prices. The strongest position combines efficient systems, reliable energy and a credible relationship with the communities hosting the infrastructure.

Model performance will continue to matter, but for many products the deciding capability may be architectural: knowing which tasks need a frontier model, which can run on a smaller one, where deterministic software is better and how to measure the cost of a successful outcome. The best product may be the one that knows how much intelligence each task deserves.

Smaller developers can compete through specialisation and discipline; larger providers have reason to improve serving efficiency and treat power as strategic. Countries such as India can pair compute access with cost-aware engineering, local applications and deliberate infrastructure planning.

Efficiency will not necessarily reduce total electricity demand: lower costs may unlock new uses faster than energy per task falls. Smaller models will not eliminate large data centres. The likely future is a mix of central infrastructure for demanding workloads, efficient systems for routine work and local inference where latency or autonomy requires it.

The next phase of AI will not be won by scale alone. It will be shaped by how much useful work can be delivered from each dollar, each accelerator and each megawatt—and by whether the infrastructure behind that work can earn public acceptance. The industry has spent years asking how large a model can become. It should now ask a harder question: how much value can the model create without demanding more resources than the product, the grid or the surrounding community can reasonably provide?

The cheapest token wins only when it helps complete something worthwhile. And it can only be generated at scale if there is enough electricity, infrastructure and public consent to keep the machines running.
