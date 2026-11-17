---
title: "Watching Isn’t Doing"
slug: watching-isnt-doing
date: 2026-11-16
topic: robotics
summary: "NVIDIA’s GR00T 2 is the strongest evidence yet that human video can ease robotics’ data bottleneck, but it supplies the what and where of physical work, not the how hard. Here is the problem in plain language, where the claims outrun the evidence, and what proof would convince me."
hero_image: /media/watching-isnt-doing/hero.webp
hero_alt: "A two-fingered robot gripper pausing over a half-tightened screw, with a smaller inset showing a head-mounted camera view of a person doing the same job."
draft: false
---

A week ago, at the Conference on Robot Learning in Austin, NVIDIA unveiled GR00T 2 and made a claim I badly want to be true: that a robot can pick up new tasks faster because it has first watched an enormous amount of people doing things. Five demonstrations, under three minutes of robot data, thirty minutes of fine-tuning on a single gaming-class GPU, and a 95% average success rate. It is a great headline.

I spent the past few days with NVIDIA’s research page, the coverage around it, and the academic work it sits on top of. Here is where I land. Human video is the first idea in robotics in years that attacks the real bottleneck instead of tiptoeing around it, and GR00T 2 is the strongest evidence yet that it works. It is also not proof that human video “solves” robotics’ data problem, and anyone who says it is, is rounding up. My view, stated plainly: video can supply the *what* and the *where* of physical work at internet scale, but it cannot supply the *how hard*, and the *how hard* is where robots still fail. NVIDIA knows this, which is why its answer is a mix of video, instrumented humans and simulation. The right bet is that mix, and the evidence for even that mix is still mostly NVIDIA grading its own homework.

One honest note on method: I worked from NVIDIA’s research page and press reporting, not from every appendix of the whitepaper. Where a claim below comes from secondary coverage I say so, and I treat those as questions rather than findings.

## The data bottleneck, in plain language

Start with why chatbots got good so fast. Language models learned from text that already existed. Every sentence anyone ever posted was a free lesson, and every lesson came with its own answer key: the next word. Nobody had to build the dataset. The internet was the dataset, roughly 300 trillion tokens of it by one commonly cited estimate.

Now try to teach a robot to fold a towel the same way. The robot needs to know what it saw, what its motors did in response, and whether the towel ended up folded. That middle ingredient, what the motors did, is the problem. It is not written anywhere on the internet. Nobody posts their joint angles and grip forces.

So the standard way to get it is teleoperation: a person remote-controls a robot while software records everything. One hour of data costs one hour of a skilled person’s labor, plus a robot, plus a space to put it in. It scales like hiring, not like downloading. The numbers are rough and vary by source, but a widely cited Bessemer estimate puts all the usable robot manipulation data in the world at around 300,000 hours, against roughly a billion hours of internet video. Other estimates run lower. One account says Physical Intelligence needed about a year to collect roughly 10,000 hours for its first foundation model. Whatever the exact figure, the gap is several orders of magnitude, and you cannot close several orders of magnitude by hiring more operators.

That is only the first of three problems. The second is portability. Data recorded on one robot’s arm, with one camera and one gripper, is awkward to reuse on another, so even those 300,000 hours are fragmented into piles that don’t talk to each other. Imagine if every language model needed its own private alphabet. The third is diversity. A robot that has practiced in a lab does not know your kitchen, your lighting, your mugs. Robots don’t just need more data. They need more kinds of it.

When I say “the data bottleneck,” I mean quantity, portability and diversity at once. Keep those three in mind, because human video is seductive precisely because it looks like it attacks all three.

## Why human video is the obvious escape hatch

People already do everything we want robots to do. They fold, pour, stack, wire, assemble and wipe, all day, all over the world, in every kind of room. Cameras are cheap, and a head-mounted camera sees the world from roughly where a robot’s camera sits, with the hands front and center. Video needs no robot in the room and no operator. It is the one data source whose supply curve looks like the internet’s instead of a payroll’s.

The industry has noticed. Tesla reportedly shifted Optimus training toward recordings of workers doing tasks. Figure says it trained a robot to navigate a home using only first-person human video. A small industry now pays people to film themselves: one report describes gig workers earning about $15 an hour strapping phones to their foreheads and washing dishes for a data vendor, and Appen says it could gather around 60,000 hours a month. Treat those vendor numbers as claims. NVIDIA’s own training mix is the louder signal. GR00T 2’s pretraining combines 402,730 hours of first-person human video, 10,184 hours of handheld-gripper demonstrations and 23,500 hours of robot teleoperation. Do the arithmetic and teleoperation is about 5.4% of the total.

The academic evidence points the same way, and I find it more persuasive than any company claim because it comes from groups using different methods. Physical Intelligence reported that human-to-robot transfer seems to emerge once a model has been pretrained on enough varied robot data, roughly doubling performance on tasks where robot data was scarce, with the benefit growing as pretraining scaled. EgoScale, using more than 20,000 hours of human egocentric data, found a log-linear relationship between how well a model predicts human actions and how much data it saw, and that this tracked real-robot performance, though it also needed a small dose of aligned human and robot data to anchor things. HumanNet reported that a model initialized on 1,000 hours of egocentric video roughly matched one initialized on 100 hours of real robot data.

Notice the exchange rate in that last result: about ten hours of video for one hour of robot data. That is a good deal when video costs a fraction of teleoperation. It also tells you human video is a *discount*, not a *miracle*. Hold that thought.

## What GR00T 2 actually shows

NVIDIA calls GR00T 2 a world-action model. In plain terms, instead of mapping “camera image plus instruction” straight to a motion, it imagines the next few seconds of video and the matching robot actions together. The bet is that predicting how a scene should change forces the model to absorb physics and task structure from human footage, and that small per-robot components can then translate the plan into motor commands for each body. It runs on parallel-gripper arms, five-fingered hands and a humanoid.

Here is the evidence I find genuinely interesting.

First, the dose-response test. NVIDIA pretrained four models on none, 1%, 10% and 100% of the human video and evaluated each on 72 tasks. Real-robot task progress rose from 50% to 70%, and progress in video rollouts from 64% to 77%. A climb that tracks the amount of human video, with the recipe otherwise held fixed, is exactly the kind of result that makes me believe the mechanism rather than the marketing.

Second, the transfer tests. In one, people wearing gloves and head and wrist cameras demonstrated four chemistry-lab tasks, and nobody teleoperated the robot to do them. A robot with two five-fingered hands lined a funnel with filter paper and wet it in 65% of trials, and NVIDIA says it succeeded on all four tasks, 20 trials each. In another, a handheld gripper demonstrated toy dump-truck assembly and a different robot arm then did it end to end, up to four minutes of work, in 60% of trials.

Third, the headline. On 50 tasks that appear in other robots’ data or in human video but never in the target robot’s own data, the model averaged 40% success zero-shot, got at least one success on 40 of the 50 tasks, reached 71% with one demonstration and 95% with five, and 37 tasks succeeded in every trial.

That is real work and I take it seriously. Now to the part I think is being underweighted.

## Where the claims outrun the evidence

**The 50 tasks were not a random draw.** By NVIDIA’s own description they are tasks that show up in other robots’ data or in human video. Secondary coverage goes further: The Decoder describes them as tasks the model already handled well after a few examples, and the Arabian Post reports that NVIDIA’s materials indicate the set was selected from tasks meeting a performance threshold after adaptation. Another outlet complains that the announcement doesn’t name the tasks or give rollout counts. I couldn’t verify each of those against the whitepaper, so treat them as open questions. But even on the charitable reading, “new tasks” means new *to this robot*, not new to the model. That is valuable cross-embodiment transfer. It is not the same as a robot that watches a video of something nobody has recorded before and then does it.

**“Forty of fifty” is a weak bar.** Succeeding once across several attempts is an existence proof, not a capability. The 40% average zero-shot success is the more honest number, and it is the one the headlines skipped on the way to 95%.

**The ablation is smaller than it looks.** I like the experiment, but read it carefully. Remove all the human video and real-robot task progress falls from 70% to 50%. That means the model with no human video, which still had the handheld data and 23,500 hours of teleoperation, was already at 50%. Human video bought twenty points. The other pieces of the mix carried the first fifty. The metric is also task *progress*, a partial-credit score, not task success, and the 1% and 10% results appear only as chart points rather than numbers I could check. I want that curve to keep bending upward, because that is what a scaling story needs. But four points, one lab’s robot and one lab’s 72 tasks is a hint, not a law.

**“Five demonstrations” is a marginal cost, not a total cost.** Under three minutes of robot data and a thirty-minute fine-tune is lovely. It sits on top of pretraining over more than 436,000 hours of data, on a cluster NVIDIA’s coverage puts at more than a thousand GB300 chips, plus task-agnostic play data so the robot learns its own body. In the no-teleoperation experiments, “zero teleoperation” means zero *task-specific* teleoperation. The robot still had to be taught what it looks like and how it moves.

**The reliability numbers are not the model alone.** The 97-or-more successes out of 100 toy assemblies come from GR00T 2 paired with a frontier reasoning model that plans steps, marks grasp points and launches recovery routines. The same post-trained policy without that agent managed 71 to 84, and supervised post-training alone 23 to 69. The Decoder adds that the robot sat idle for roughly a third of one trash-sorting task waiting, on average over seven seconds, for the planner, that success rates on the human-transfer lab tasks ranged from 10% to 80%, and that wiping up a spill with a towel under the humanoid’s foot worked in just under half of attempts.

**Nobody outside NVIDIA has run it.** Code is promised for December. Independent benchmarks tell a humbling story, though not a head-to-head one: the RoboDojo paper reported a best real-world score of 12.8% across 30 policies, while human experts scored 100%. Different suite, different tasks. That is not evidence GR00T 2 would score 12.8%. It is evidence that task design moves success rates enormously, which is exactly why a self-selected task set can’t be compared to anything.

None of this makes GR00T 2 fraudulent. It is an ordinary vendor paper with ordinary vendor choices. But “Can human video solve robotics’ data problem?” is not a question a vendor paper can settle.

## The physics video can’t carry

Here is my deepest reservation, and it holds even if every number above survives replication. Video shows what happened. It does not show how hard anyone pushed.

Watch someone tighten a screw. The camera sees a wrist turning. It does not see torque. Seat a memory module, thread a plug, wipe a spill: the difference between success and failure is often a force or a vibration that no lens records. NVIDIA’s own team acknowledges the model doesn’t yet take in direct touch data and sometimes misses subtle errors such as a half-turned screw.

The telling detail is what NVIDIA did to improve contact-rich work. Three insertion tasks sat at 40 to 76% after supervised post-training. Real-world reinforcement learning, meaning the robot practicing against a success signal, lifted them to 88 to 96%. The thing that fixed contact was not more video. It was the robot trying, failing and trying again.

The second telling detail is that the most impressive “from humans” results don’t use ordinary video. The funnel demos came from people wearing gloves and cameras. The breakfast and match-striking demos used DexUMI, a wearable exoskeleton that mirrors the robot’s fingers so human motion arrives already shaped like robot motion. The truck assembly used a handheld gripper. That is learning from humans, yes, but from humans instrumented to make their behavior legible to a robot. I think that is the honest middle. Human demonstration is a spectrum from YouTube to exoskeleton, and the closer to the robot’s body you get, the better it works. Raw footage of a person making coffee is the cheapest end of that spectrum and the weakest signal.

NVIDIA also points to an open-source hardware site for its GEAR UMI and DexUMI prototypes, the handheld gripper and wearable exoskeleton behind those demos. I haven’t audited exactly what the release contains, but if designs and software really are available, that matters more than it sounds. It lowers the price of the force-aware end of the spectrum, so any lab can collect that kind of data, and it shifts the exchange rate I keep asking about.

## The strongest rebuttal: simulate the force

To be fair, NVIDIA is not betting on video alone, and the best rebuttal to my physics complaint sits in the same announcement. Isaac Lab 3.0 adds a reinforcement-learning post-training library and lets users choose the Newton physics engine alongside PhysX. The GR00T 2 page shows what that buys. Starting from a single human demonstration of using a hammer, the team reconstructed the task in simulation, refined it with reinforcement learning, and transferred it to a real robot with Sharpa hands. On the Unitree G1, adding simulated data raised out-of-distribution success for GR00T 2 Turbo from 6.7% to 63.3%. NVIDIA also reports that policy rankings in its simulated digital twins track real-world rankings closely, with a Pearson correlation around 0.92 across 14 policies on a 25-task benchmark.

Read that as a division of labor: video supplies the task, simulation supplies the force. It is a more coherent story than video alone, and it is a big reason my bet below is a mix. But I would not let it close the case. Simulation has its own reality gap, especially for deformable objects and fine contact. These are, again, NVIDIA’s numbers on NVIDIA’s tasks, and the 63.3% is one humanoid’s out-of-distribution test. Simulation moves the force problem. It doesn’t dissolve it.

## What evidence would convince me

Here is my actual checklist. If these arrive, I will say the bottleneck is largely broken. Until then, I will say “promising.”

**1. A frozen, named task list with per-task results.** Choose the tasks before seeing outcomes, publish every one, show the rollout count behind each number with confidence intervals, and include the failures. NVIDIA’s own evaluation team has written that few rollouts mean wide uncertainty. Per the Tech Times summary of that post, 90% on 70 rollouts is compatible with anything from roughly 80% to 96%. Hold the flagship claim to NVIDIA’s own standard.

**2. Outside replication on tasks the authors didn’t pick.** Weights and code are due. When they land, I want a lab with no stake to run the model on a different robot, against a task list drawn by someone else, ideally a standing benchmark with hidden tasks. Crucially, some of those tasks should be absent from the pretraining mix, to separate “learns new skills from video” from “remembers tasks it saw on another body.”

**3. A matched-budget fight against the boring alternatives.** Price out collecting and curating hundreds of thousands of hours of human video. Spend the same money on robot teleoperation, on more diverse robot data, and on simulation. Which wins? And does human video’s advantage shrink or grow as robot data grows? Physical Intelligence’s result says it grows with scale, while other work says you need alignment data. This is the most important unresolved number: the exchange rate between a human hour, a robot hour and a simulated hour, measured on task *success*, with every intermediate point published.

**4. Zero-teleoperation transfer on force-critical tasks.** Show me human-only demonstrations carrying over to tight-tolerance insertion, tightening and deformable objects, reported by task category, with and without a simulation stage. If video alone helps there, I will happily revise my physics argument. If it doesn’t, we learn exactly where the ceiling is and how much the simulator is carrying.

**5. Reliability a factory would recognize.** A 95% average across tasks is a demo number, and a line that fails one cycle in twenty is a broken line. I want thousands of consecutive cycles on one task, interventions per hour, time to recover, and robustness to new lighting, new objects and a different table, with the planner’s latency counted rather than hidden.

**6. Full cost accounting per skill.** Include video procurement and curation, capture hardware, alignment and play data, compute, fine-tuning and engineer time, and compare against teleoperation at equal quality. “Five demonstrations” is the marginal price. I want the amortized one. Open capture hardware should make that bill smaller, and I would like to see by how much.

**7. A scaling curve that keeps going, and a data supply I can trust.** Show the human-video curve on a log axis, past the current range, without flattening. And tell me where the footage comes from. NVIDIA has released 100,000 hours openly as Human-1M-100K, which helps, but one analysis notes the rest is bought from vendors. If the technique depends on people paid to film their homes and workplaces, I want to know how durable, consensual and affordable that supply chain is. Reports of Tesla factory workers objecting to data collection that might automate their own jobs suggest this is not a footnote.

## My bet

My prediction, held with moderate confidence: human video will become to robots what web text was to chatbots, a giant, cheap, imperfect pretraining diet that gives models a broad prior about tasks, scenes and how hands move. It will not be what makes a robot reliable. That polish will come from robot-specific data: simulation, the robot’s own practice, and deployed fleets. Bessemer’s analysts make a version of this point: a company with hundreds of robots in real facilities owns contact-rich data that video collectors can’t match. In between sit instrumented humans, with gloves, exoskeletons and handheld grippers acting as the bridge.

Under that picture the data problem changes shape. The question stops being “how do we get more?” and becomes “what is the cheapest ratio?” An early preprint, XRZero-G0, reports performance comparable to all-robot data from a 10:1 mix of robot-free to real-robot data at roughly a twentieth of the acquisition cost. I’d bet we see a lot more ratio papers in the next year, and I’d bet the answers vary a lot by task.

So, can human video solve robotics’ data problem? It can plausibly solve most of the quantity problem and a good chunk of the diversity problem, and GR00T 2 shows real progress on portability. It cannot, by itself, tell a robot what contact feels like. Until someone outside NVIDIA shows otherwise, on tasks NVIDIA didn’t choose, I’m treating GR00T 2 as a strong signal rather than a verdict. Watch the December code release. That is when this stops being a press release and becomes a science question.

---

## Sources I leaned on

- NVIDIA GEAR, *GR00T 2: Scaling Robot Foundation Models for Generalization, Dexterity, and Adaptation* (research page, November 2026): https://research.nvidia.com/labs/gear/gr00t-2/
- The Decoder, “Nvidia’s model GR00T 2 watches humans on video, then imagines itself as the robot” (Nov 10, 2026): https://the-decoder.com/nvidias-model-gr00t-2-watches-humans-on-video-then-imagines-itself-as-the-robot/
- Tech Times, “NVIDIA GR00T 2 Robot Model Reports 95% Success While Leaving 50 Test Tasks Unnamed” (Nov 10, 2026), also the source for the Isaac Lab 3.0 and Newton details: https://www.techtimes.com/articles/330365/20261110/nvidia-gr00t-2-robot-model-reports-95-success-while-leaving-50-test-tasks-unnamed.htm
- Arabian Post and Pebblous coverage of the task-selection and data-mix questions: https://thearabianpost.com/nvidia-presents-gr00t-2-for-demonstration-trained-robot-tasks/ and https://blog.pebblous.ai/blog/nvidia-groot-2-human-video-data-provenance/en/
- Physical Intelligence, “Emergence of Human to Robot Transfer in VLAs”: https://www.pi.website/research/human_to_robot
- EgoScale (arXiv 2602.16710) and HumanNet (arXiv 2605.06747)
- Bessemer Venture Partners, “Robotics and physical AI” predictions: https://www.bvp.com/atlas/bessemer-predicts-robotics-and-physical-ai
- Origin Data Partners, Startup Fortune and aiforautomation.io reporting on Tesla, Figure and gig-worker data collection (vendor and secondary claims, treated as such)
- XRZero-G0 (arXiv 2604.13001, preprint)
