---
title: "The Pipes Are the Risk"
slug: the-pipes-are-the-risk
date: 2026-11-17
topic: finance
summary: "A Federal Reserve survey found AI was the most cited threat to financial stability among market contacts. The danger may lie less in the models than in the debt, guarantees and autonomous systems built around them."
hero_image: /media/the-pipes-are-the-risk/hero.webp
hero_alt: "Placeholder: cutaway of a building's pipes and wiring, one joint visibly leaking."
medium_url: ""
draft: true
---

On Friday the Federal Reserve published a number that deserved more attention than it got. In the survey section of its semiannual Financial Stability Report, 87 percent of the 23 market contacts the New York Fed spoke to named AI as a salient risk to the financial system, up from 50 percent in the spring. It was the most frequently cited potential shock, ahead of a correction in risk assets (52 percent) and higher long-term rates (48 percent). The sample is small, and the report is explicit that the responses are not the views of the Federal Reserve Board.

Then on Monday Governor Michael Barr, speaking for himself, gave what may be the most important speech about AI that almost nobody in AI will read. Read it and notice what isn't there: no superintelligence, no jobs forecast, no alignment debate. What's there is debt, guarantees, special purpose vehicles, lease commitments that haven't started yet, and a warning that software agents could run a bank in minutes.

The people paid to worry about the whole system are not worrying about the model. They're worrying about the pipes. I think they're right, and the rest of us, the builders and the pundits who argue about benchmarks and bubbles, have been staring at the wrong layer.

## Two kinds of loss

In finance the question that matters is never whether prices will fall. They always do eventually. The question is who is holding the asset when they fall, and whether they knew they were.

Look at the last two weeks. The Nasdaq is more than 10 percent below its October high. Nvidia is roughly 40 percent under its peak after its chief executive abruptly stepped down. This is the loud kind of loss: painful, public, and borne by people who bought equity at a price they could read on a screen. A shareholder watching a stock drop 40 percent has been handed the bill for a risk they knowingly took. That's the market doing its job.

The quiet kind of loss is different. It lands in a life insurer's general account, in a private credit fund that has to gate redemptions, in a bank's credit line to a vehicle most of its depositors have never heard of. It lands on whoever holds the junior slice of a structure designed by people who got paid when it was sold. Those holders didn't pick a risk. A chain of intermediaries assigned one to them, and the purpose of the chain was to make the assignment hard to see.

Barr put the problem plainly: this kind of complexity makes it hard to know where the risk actually sits, and that opacity makes selloffs worse when sentiment turns. It's the whole argument in one sentence. A loss you can locate is a loss you can price, and a loss you can price is one a market can absorb. A loss nobody can locate gets priced all at once, by everyone, at the worst possible moment.

So my first claim is that the stock correction is the least interesting thing happening. The Fed's report, whose data run through late October, called markets orderly. What it flagged was underneath the prices.

## The debt

Start with the part that has numbers. The Fed says debt issued to finance advanced computing infrastructure passed $680 billion by October, about five times what was issued in all of 2023. It now makes up roughly 31 percent of nonfinancial investment-grade corporate issuance, up from under 6 percent in 2023. Public debt outstanding is estimated above $1.1 trillion, and that leaves out most of the private credit, which nobody can measure properly. Barr said the on-balance-sheet debt of the seven largest AI firms is expected to pass $800 billion before the year is out.

The reason is simple: the buildout is outgrowing its own cash. A Brookings conference draft from September projects combined capital spending by Oracle, Microsoft, Amazon, Meta and Alphabet at more than $800 billion in 2026, up from about $97 billion in 2020 and over $400 billion in 2025. That would exceed their estimated combined operating cash flow of roughly $707 billion for the first time. The measure includes some non-AI spending, so it overstates the AI bill, and 2026 is a projection, not a completed year. The direction is hard to argue with, though. Some of the most profitable companies in history can no longer pay for the thing out of pocket. That's the moment the story stops being about technology and starts being about credit.

Debt is also the smaller half. The larger half is what doesn't get called debt. As of the second quarter, the Fed estimates, leases not yet started, take-or-pay contracts and residual value guarantees across seven large technology firms exceeded $3 trillion: more than $1 trillion of leases and more than $2 trillion of the rest. Those figures are undiscounted, and they're dated a few months earlier than the $680 billion issuance number, so the two can't be added or compared cleanly. Direction still beats level. The promises are growing faster than the borrowing, and promises are exactly what a balance sheet doesn't show.

## Anatomy of one deal

The clearest way to see this is a single deal, and the best documented is Meta's Hyperion campus in Louisiana. The project is about $30 billion of data center and power, which excludes the computing hardware Meta finances separately as the tenant. Meta sold 80 percent of the joint venture to Blue Owl for roughly $2.5 billion of equity, and in October 2025 the venture borrowed $27 billion in A+ rated bonds, the largest investment-grade corporate issue in US history. Do the arithmetic: roughly 90 percent debt against the financed assets, with debt service covered just 1.12 times. Meta's own leverage at the corporate level is about 25 percent of book equity and 4 percent of market equity. One project, one tenant, two very different leverage pictures depending on which door you walk through.

Meta pays for the privilege. The bonds yielded 6.58 percent, at least a full point more than Meta would likely have paid on plain unsecured debt, which Brookings puts at more than $5 billion of extra interest over the life of the deal, ultimately reflected in Meta's lease payments. A company throwing off roughly $130 billion a year in operating cash flow is willing to pay billions to look lighter. If reported leverage didn't matter, nobody would pay. Since someone does, reported leverage is the thing being managed.

The lease design is where it gets interesting. Five four-year leases start in 2029 against bonds that mature in 2049, and at each renewal Meta can walk away from some or all of the campus as long as it covers any shortfall against a stated minimum value. Under current accounting Meta books neither the future leases nor that guarantee until they take effect, even though, as the paper dryly observes, one of the two will certainly come due. Put it together: a twenty-year bond against a campus designed around today's rack densities and cooling, a tenant that can leave every four years if it makes up the difference, and a guarantee that could be called in exactly the scenario where AI demand disappoints, when the guarantor's own business may be under pressure and the collateral is worth least. Finance people call that wrong-way risk. It looks to me like the central design flaw of the era.

None of this means Hyperion blows up. A tenant with that much cash flow can carry it. The worry is that it's a template. A near-identical El Paso deal tied to Meta and BlackRock priced $12.3 billion of A+ bonds in July, and templates get copied. The first deal is underwritten by a company with $130 billion of cash flow. The tenth may be underwritten by whoever is left. Barr noted that lower-rated firms most dependent on outside funding are already moving to more complicated asset-backed deals. A structure can travel down the credit curve unchanged. The credit doesn't.

## The guarantee loop

Barr counts more than $100 billion of cumulative equity investment by hyperscalers and GPU makers in model labs and cloud startups. The recipients spend it renting or buying GPUs from the people who handed them the money. That's circular financing, a dirty phrase, but fairness matters here. Against a hyperscaler's balance sheet $100 billion is small, and the recipients can in principle replace supplier money with customer money one day. Circularity is a bridge, not a crime.

It gets more worrying when the circle acquires a backstop. In August Nvidia announced preliminary memoranda with Apollo, BlackRock, Blackstone, Brookfield, Goldman Sachs and KKR, aimed at mobilizing more than $500 billion of outside capital to finance its chips. That figure is a target, not committed money. Nvidia says it may, case by case and at its option, provide residual-value support for up to 25 percent of an opportunity, and that the lenders still underwrite the customer, the demand and the cash flows. Applied across the whole target, that ceiling would be $125 billion, which is how Brookings frames the potential exposure. It isn't a liability today, and it may never become one.

But look at the design. Once a lender lends partly because the supplier has stood behind the resale value of the chips, the lender is underwriting the guarantor as well as the borrower and the hardware. The guarantor becomes a possible single point of failure for a web of loans whose value rests on the same demand curve as everything else. Jensen Huang, then Nvidia's chief executive, presented the platform as an answer to the circularity charge. A circle isn't broken by having the supplier guarantee the collateral. One credit analysis sets Nvidia's roughly $63 billion of cash and securities and $97 billion of annual free cash flow against that ceiling: comfortable in a good year, different in a bad one.

The academic evidence says the rest of the complex has the same problem. Data center REITs used to behave like defensive infrastructure, with a market beta near 0.5. It's now near 1, and their sensitivity to the non-AI parts of the S&P is comparable to their sensitivity to AI stocks. Diversification is what you call correlation you haven't measured yet.

## The best objection

The strongest objection to everything above is that the assets are fine. GPU rental prices have gone up this year, not down. One tracker has H100 rents up about 38 percent since January and the six-year-old A100 up 20 percent, and Barr himself noted that lease rates for older chips are holding. The telecom comparison is also imperfect: fiber lasted decades, and the railroads left us with railroads. The big banks are well capitalized, the equity risk premium is low but nowhere near its dot-com lows, and Barr says he's less worried about direct losses because the debt behind the boom is still limited.

I accept most of that, and it doesn't change my view, because the question isn't whether the forecast is right. A financial structure is good if it survives being wrong. Rental prices rise in a shortage, and shortages end; that's what makes them shortages. Brookings runs the arithmetic on what its central buildout scenario needs. Earning a 10 percent unlevered return on the 183 gigawatts of additional US capacity in that scenario requires about $3.7 trillion of mature annual revenue at a 50 percent operating margin. For scale, the two biggest labs together make roughly $100 billion a year today. They won't be the only source of demand, since cloud, enterprise and consumer spending all count, but if those two alone had to fill the gap it would take growth of about 80 percent a year until 2032. Somewhere in the ecosystem, a lot of growth is being assumed. And if chips turn out to last three years instead of six, the requirement rises to about $6 trillion.

I'll add a view from my own corner. I work on inference and quantization, and every time someone makes a model cheaper to serve, a lender somewhere should wince. Ternary weights, mixture-of-experts, better kernels: none of that is a threat to AI. It's a threat to the price of a GPU-hour, which is the unit every one of these structures is denominated in. Maybe Jevons saves them and cheaper intelligence means more demand than anyone can supply. Maybe it doesn't. Efficiency is good for the world and bad for collateral, and it's the scenario the guarantees are least likely to be priced for.

## The fast part

Everything so far moves at the speed of credit. The second half of Barr's speech is about something that moves at the speed of software, and it's the part I find most unsettling.

Barr warned that AI agents could detect yield differentials or signs of stress at a bank and move deposits automatically, accelerating a run to minutes and overwhelming both liquidity management and the regulators' ability to respond. He said major banks are already finding AI agents attempting actions in retail customer accounts, with no way to verify authenticity, consent, or alignment with what the customer asked for. And he noted that this year's incidents have shown models treating security boundaries as obstacles to get around rather than rules to follow.

On Monday California's attorney general sued OpenAI over a July incident in which, according to the complaint, hundreds of agents running on experimental models attacked Hugging Face, one of at least 80 such incidents the state alleges. These are allegations, not findings. OpenAI says it takes misalignment seriously and is engaging constructively with the attorney general's office. The case leans on existing law, public nuisance and unfair competition, and it tests a lab's duty to contain agents during testing. Who pays when a deployed agent moves a customer's money is a different question, and I haven't seen a settled framework for it.

Financial stability is a race between the speed of a panic and the speed of the response. Silicon Valley Bank lost about $42 billion of deposits in a single day in March 2023, in the age of smartphones and group chats, and regulators still had only hours. Every tool we have, deposit insurance, the discount window, trading halts, the weekend resolution, assumes a loop in which a human wakes up, reads something and makes a call. Agents could compress that loop from days to seconds, across millions of accounts at once, running on a handful of foundation models with the same priors and the same blind spots. Barr points to research warning that markets full of similar models can herd, and that a flaw shared by many models can fail in many places at the same moment.

We've seen rehearsals of automated, correlated failure. The quant unwind of August 2007, the flash crash of May 2010, and Knight Capital's loss of roughly $440 million in 45 minutes in 2012 were all fast and machine-driven. Each was bounded, though, to a market, a venue, a strategy or a single firm. The new element isn't automation. It's reach and uniformity: the same decision logic acting inside retail accounts at many institutions, through a few shared models, with no single venue to halt.

The same small set of firms may also sit on both sides: borrowers and tenants in the financing web, model suppliers in the agent layer. A shock that hits one could hit the other. That's what concentration looks like once it has spread into two systems at once.

## What I'd do

Here is what I'd want, roughly in order of how cheap it is.

First, publish the guarantee table. Every lease not yet started, every residual value guarantee, every take-or-pay commitment, with the counterparty, the tenor and the assumed recovery value, consolidated and in one place. Nobody should need ten filings and a Moody's note to work out what a single hyperscaler owes.

Second, stress them together. The Fed says the largest US bank holding companies have close to $1 trillion of exposure to big tech, data center developers, related special purpose vehicles, private credit funds and utilities, and that these are evaluated in the annual stress test. Good. Now run the scenario where the guarantor's credit weakens, chip resale values halve and tenants shrink their leases in the same quarter. Correlation of one. Anything less tests the structure in the weather it was built for.

Third, match tenor to asset life. Nobody should be selling long-dated paper against assets whose economic life may be much shorter, GPUs above all, unless amortization reflects it. That isn't exotic. It's the oldest rule in lending.

Fourth, give agents speed limits and scoped permissions. Velocity caps on agent-initiated transfers, cooling-off windows for large moves, bank-side kill switches, per-action consent, and liability that lands on whoever deployed the agent, not on the customer who clicked yes once. Identity matters too, and the Linux Foundation launched the Agent Name Service as a project on November 10 to provide it. But knowing which agent is acting says nothing about what it's allowed to do, or whether this particular transfer was something the customer agreed to. Identity answers who. A bank also needs to know whether, and how much. We have circuit breakers on stock exchanges because we learned the hard way that speed needs a ceiling. Bank deposits deserve the same.

## The railroad survived

None of this is a bubble call. If the demand arrives, these structures will look prescient, the campuses will fill, and in twenty years we'll be glad of the capacity the way we're glad of the highways and the fiber.

But real technology and fragile financing is the default configuration of every great infrastructure boom. The railroads were real, and the Panic of 1873 happened anyway, set off when Jay Cooke and Company, a financier of railroads, couldn't roll its paper. The railroads survived. A lot of the people who financed them, and a lot of the savers behind those people, did not. The technology doesn't have to fail for the financing to. It only has to show up a little later than the spreadsheet said.

That's what I'd take from the Fed survey's 87 percent. Not that AI is dangerous, or overhyped, or a fraud. That somewhere in the last two years, enormous promises were written against a price path, by firms whose fortunes rise and fall on the same curve, and wrapped in structures designed to be hard to see. This week the largest AI listing yet is scheduled to price, and Nvidia reports its first earnings without Jensen Huang at the helm. Whatever the market says, the real test isn't what the stocks do. It's what's sitting underneath them, who is holding it, and whether they know.

Ask not whether the models work. Ask what promises were written for the day they're worth less.

## Sources

- Federal Reserve Board, *Financial Stability Report*, November 2026: https://www.federalreserve.gov/publications/files/financial-stability-report-20261113.pdf
- Governor Michael Barr, "Some Potential Financial Stability Implications of Artificial Intelligence," November 16, 2026: https://www.federalreserve.gov/newsevents/speech/barr20261116a.htm
- Stijn Van Nieuwerburgh, "Financing the AI Buildout," Brookings Papers on Economic Activity conference draft, September 2026: https://www.brookings.edu/wp-content/uploads/2026/09/4c_Van-Nieuwerburgh.pdf
- Reuters (syndicated), "Wall Street ends sharply lower on AI jitters ahead of Nvidia results, Anthropic IPO," November 16, 2026: https://finance.yahoo.com/markets/stocks/articles/p-500-nasdaq-futures-slide-104351968.html
- CoinDesk, "Nvidia faces first earnings test without Jensen Huang as AI stocks slide," November 17, 2026: https://www.coindesk.com/markets/2026/11/17/nvidia-faces-first-earnings-test-without-jensen-huang-as-ai-stocks-slide
- Implicator, coverage of Nvidia's August 10 financing announcement and the "up to 25%" residual-value support: https://www.implicator.ai/nvidia-enlists-six-wall-street-firms-to-target-500-billion-for-ai-compute/
- Sascha Steffen, independent credit analysis of Nvidia's financing platform: https://www.sascha-steffen.de/updates/nvidia-500bn-ai-financing-credit-risk
- Analytics India Magazine, on Silicon Data GPU rental prices: https://analyticsindiamag.com/ai-features/why-nvidias-six-year-old-gpu-is-still-making-money
- NPR, "California sues OpenAI over hacking risks," November 16, 2026: https://www.npr.org/2026/11/16/nx-s1-6042920/california-sues-openai-hugging-face-hacking-incident
- The Hill, "California attorney general sues OpenAI over alleged safety failures," November 16, 2026: https://thehill.com/homenews/state-watch/6223583-california-sues-openai-huggingface-hack/
- Linux Foundation, "Linux Foundation Welcomes Agent Name Service...," November 10, 2026: https://www.linuxfoundation.org/press/linux-foundation-welcomes-agent-name-service-to-bring-verifiable-identity-and-discovery-to-ai-agents
