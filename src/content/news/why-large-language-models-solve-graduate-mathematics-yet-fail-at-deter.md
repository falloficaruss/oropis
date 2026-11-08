---
title: Why Large Language Models Solve Graduate Mathematics Yet Fail at Deterministic
  Board Games/
description: This post analyzes why frontier large language models (LLMs) can solve
  graduate-level mathematics yet routinely blunder against intermediate chess players,
  attributing the capability gap to architectural and structural asymmetries
pubDate: '2026-11-08T08:46:40+00:00'
author: OropisHQ
beat: AI
archetype: research
format: analysis
tags:
- LLM
- Chess
sources:
- name: https://oropis.com
  url: https://oropis.com
facts: {}
updatedDate: '2026-11-08T08:47:38+00:00'
hero: /media/why-large-language-models-solve-graduate-mathematics-yet-fail-at-deter/hero.webp
heroCredit: informationdifference.com
heroAlt: chess
---

## 1. Introduction: The Capability Discrepancy

Recent evaluations of frontier large language models (LLMs) present an apparent contradiction in artificial intelligence capabilities. The same autoregressive transformer architectures that successfully resolve graduate-level problems in algebraic topology, real analysis, and combinatorics frequently fail to play a legal, tactically sound game of chess against an intermediate club player. When operating without external calculation engines or specialized verification harnesses, general-purpose language models routinely miss two-move tactical refutations, lose track of piece coordinates, or generate illegal moves once a game departs from standard opening theory.

To a casual observer, this performance gap appears backwards. Human culture has historically treated chess and abstract mathematics as adjacent benchmarks of raw analytical intellect. Furthermore, from a formal systems perspective, chess appears considerably simpler than open-ended mathematical research. Chess is a finite, deterministic, two-player game of perfect information played on an 8x8 grid with 64 squares and six distinct piece types. Its state space is large, with a game-tree complexity estimated near $10^{120}$ and a legal state-space complexity around $10^{44}$, yet the rules governing state transitions are rigid, simple, and exhaustively specified. Graduate mathematics, by contrast, operates over infinite domains, requires the synthesis of disparate definitions across vast literature, and allows an unbounded set of potential proof strategies.

Why, then, does a model capable of navigating abstract mathematical spaces struggle to maintain coherence on a 64-square board?

The explanation does not lie in a failure of general "intelligence," a term that obscures more than it clarifies when evaluating neural architectures. Instead, the discrepancy stems from the structural mechanics of autoregressive sequence modeling, the geometry of representation in token space, the mathematical distinction between existential proof search and adversarial minimax optimization, and the engineering economics of test-time compute. Examining each of these factors reveals where associative language modeling ends and explicit state-space search begins.

---

## 2. Autoregressive Generation versus Explicit Tree Search

To understand why an unassisted language model blunders on a chessboard, one must compare how a transformer generates a sequence of tokens with how a dedicated chess engine selects a move.

### The Mechanics of Next-Token Prediction

A standard decoder-only transformer models the joint probability distribution of a text sequence $x = (x_1, x_2, \dots, x_T)$ by factoring it into a product of conditional probabilities:

$$P(x) = \prod_{t=1}^{T} P(x_t \mid x_1, x_2, \dots, x_{t-1})$$

When an LLM plays chess in a standard chat interface, the game history is presented as a sequence of Portable Game Notation (PGN) tokens, such as `1. e4 e5 2. Nf3 Nc6 3. Bb5 a6`. To select its next move, the model performs a single forward pass through its fixed stack of transformer layers, projecting the hidden state of the final token onto the vocabulary logits to sample the next move token.

Crucially, the computational budget allocated to generating that single token is constant, bounded by the depth $L$ and width $d_{\text{model}}$ of the network. Whether the board position is a trivial recapture on move 4 or a sharp, tactical complication on move 28 where ten pieces hang simultaneously, a standard autoregressive pass executes the exact same number of floating-point operations per generated token. Even when using reasoning-oriented models that generate an internal chain-of-thought (CoT) scratchpad prior to outputting a final move, the model is still generating a linear stream of text tokens. It does not possess a native data structure for branching, backtracking, or pruning an explicit state tree in memory.

### How Dedicated Chess Engines Compute

Contrast this linear generation with a traditional chess engine like Stockfish or a neural Monte Carlo Tree Search (MCTS) engine like AlphaZero and Leela Chess Zero (Lc0). A chess engine is fundamentally a search algorithm paired with an evaluation function.

1. **State Representation:** Traditional engines do not represent the board as a historical string of algebraic moves. They maintain an explicit, mutable board state, almost universally implemented via **bitboards**: sets of 64-bit unsigned integers (`uint64_t`) where each bit corresponds to a square on the 8x8 grid. Separate bitboards track white pawns, black knights, occupied squares, and attack masks. Updating a position or checking whether a square is attacked requires a handful of bitwise operations (`AND`, `OR`, `XOR`, bit shifts) that execute in single CPU clock cycles.
2. **Move Generation:** From the current bitboard state, a deterministic move generator enumerates all strictly legal moves. It is architecturally impossible for Stockfish to output an illegal move because the transition function is hard-coded into the move generator.
3. **Tree Search and Backtracking:** Rather than committing to a move in a single forward pass, the engine constructs a lookahead tree. In alpha-beta engines, the search explores variations to depths of 20 to 40 ply (half-moves), using techniques like null-move pruning, late move reductions (LMR), and transposition tables (via Zobrist hashing) to discard inferior branches and avoid recomputing identical positions reached via different move orders.
4. **Leaf Evaluation:** At the leaves of this search tree, an evaluation function assigns a scalar score to the board state. In modern engines using Efficiently Updatable Neural Networks (NNUE), this evaluator is a shallow, heavily quantized neural network optimized for SIMD instructions on CPU registers, evaluating tens of millions of positions per second.

When an LLM plays chess without a search harness, it is attempting to approximate the result of a 30-ply minimax search tree using only its static, single-pass value/policy prior. Even AlphaZero's raw policy network, which was trained specifically on tens of millions of self-play chess games, plays significantly weaker chess when its MCTS lookahead is disabled and it is forced to select moves purely from its raw policy head. Asking a general-purpose text model to match a search engine without a search tree is an apples-to-oranges architectural comparison.

### Compounding State Errors over Long Horizons

Because a language model normally receives the game as a list of moves (e.g., `1. d4 Nf6 2. c4 e6 ... 24. Rxe4`), it must reconstruct the current board state implicitly within its activation layers on every turn.

In a Markov decision process like chess, the optimal action depends solely on the current board state $S_t$, not the historical trajectory $h_t = (a_1, a_2, \dots, a_{t-1})$ that produced it (ignoring three-fold repetition and the 50-move rule). However, a PGN prompt gives the LLM the trajectory $h_t$ rather than the explicit state $S_t$. To know whether the square `d5` is currently vacant on move 25, the model's attention heads must trace every move in the context window that moved a piece onto or off of `d5`, resolve captures, and track which pieces block sliding rays along files, ranks, and diagonals.

If the model's internal representation suffers a minor attention failure at move 18—for instance, failing to register that a bishop on `c4` was captured or moved to `b3`—every subsequent calculation relying on the `a2-g8` diagonal becomes corrupted. In natural language generation, a minor semantic drift in paragraph three rarely invalidates paragraph four. In a deterministic state machine like chess, a single state-tracking error invalidates the entire downstream calculation.

---

## 3. Structural Differences Between Mathematics and Adversarial Games

If autoregressive generation struggles with exact state tracking and tree search, why do modern LLMs perform remarkably well on graduate-level mathematics and competitive programming benchmarks? The answer lies in the topological and logical differences between mathematical proof spaces and two-player zero-sum games.

| Structural Dimension | Mathematical Problem Solving | Chess (Adversarial Game) |
| --- | --- | --- |
| **Logical Quantifier Structure** | Existential ($\exists$): Find *at least one* valid derivation path from premises to conclusion. | Alternating ($\exists \forall \exists \forall$): Find a move such that *for all* opponent replies, a winning continuation exists. |
| **Path Redundancy** | High: Multiple theorems, lemmas, or coordinate systems can prove the same result. | Low in tactical positions: Often only a single exact move avoids immediate defeat. |
| **State Representation** | Explicit in context: Every equation or logical step is written out as part of the proof text. | Implicit in PGN: The 2D board geometry is hidden behind a historical list of algebraic deltas. |
| **Error Tolerance during Search** | High: A dead-end algebraic manipulation can be abandoned in the scratchpad without penalty. | Zero at execution: Once a move is played on the board, the state transition is irreversible. |
| **Semantic Continuity** | High: Related mathematical concepts cluster together in natural language embedding space. | Discontinuous: Changing a single coordinate character (`Nxf7` vs. `Nxf6`) flips an evaluation from winning to losing. |

### Existential Proofs versus Alternating Quantifiers

From the perspective of computational complexity and formal logic, proving a mathematical theorem and winning a chess game belong to fundamentally different complexity classes.

Finding a mathematical proof of bounded length is an **existential** search problem (analogous to $\text{NP}$). Given a theorem statement $T$, the solver needs to exhibit a single valid sequence of logical deductions $P = (s_1, s_2, \dots, s_n)$ such that $s_n = T$ and each step $s_i$ follows validly from prior steps and axioms. If fifty potential proof strategies fail and one succeeds, the solver only needs to present the one that succeeded. Furthermore, during a chain-of-thought reasoning trace, if the model attempts an integration by parts that leads to an intractable expression, it can simply write, "That approach does not simplify; let us try a trigonometric substitution instead," and continue within the same context window. The failed branch does not corrupt the problem state.

Chess, by contrast, is governed by **alternating quantifiers** ($\exists \forall \exists \forall \dots$), the hallmark of $\text{PSPACE}$-complete and $\text{EXPTIME}$-complete games. To prove that a move $m_1$ is sound, it is entirely insufficient to show that there exists *some* sequence of moves where the player wins (known in chess parlance as "hope chess"). The player must verify that *there exists* a move $m_1$ such that *for all* legal opponent replies $r_1$, *there exists* a counter-move $m_2$ such that *for all* opponent replies $r_2$, the resulting evaluation remains favorable:

$$\exists m_1 \in \mathcal{M}(S_0) \; \forall r_1 \in \mathcal{M}(S_1) \; \exists m_2 \in \mathcal{M}(S_2) \; \forall r_2 \in \mathcal{M}(S_3) \dots V(S_k) \ge \theta$$

This universal quantifier ($\forall$) is the Achilles' heel of linear chain-of-thought reasoning. When an LLM reasons through a chess position in text, it naturally samples high-probability continuations—variations that look standard or thematic. However, refutations in chess often rely on a single low-probability, counter-intuitive tactical resource available to the opponent (such as an intermediate check, a quiet prophylactic move, or a queen sacrifice). If the LLM's linear scratchpad examines the three most obvious opponent replies and overlooks the fourth forcing reply, its entire evaluation of the candidate move is wrong. Because the model cannot exhaustively enumerate and evaluate every branch in its context window, a single omitted branch in a universal quantification causes catastrophic failure.

### Redundancy and Semantic Smoothness in Mathematics

Higher mathematics also exhibits a property that aligns well with high-dimensional vector embeddings: **structural redundancy**.

Suppose a graduate problem requires bounding a difficult integral or proving an inequality over a normed vector space. Typically, there is not one unique sequence of symbols that achieves this. A proof might proceed via the Cauchy-Schwarz inequality, or via Hölder's inequality, or by passing to the Fourier domain, or by applying Jensen's inequality to a convex function. In the training corpus of an LLM, these techniques are surrounded by rich, descriptive natural language explaining *why* a certain tool applies (e.g., "To bound the cross-term, we exploit orthogonality...").

Consequently, in the transformer's embedding space, the problem statement and the applicable proof techniques share strong semantic similarity. High-level mathematical reasoning often operates at the level of **macro-actions** (applying named theorems, invoking canonical constructions, or reducing a problem to a known normal form). Once the model identifies the correct macro-strategy through semantic association, filling in the algebraic steps is a localized, short-horizon task where each intermediate equation is explicitly written into the context window.

Chess lacks this semantic smoothness at the tactical level. Consider two board states that are identical except that a white pawn sits on `h2` in Position A and on `h3` in Position B. In semantic or visual terms, the two positions are 98% identical. Yet in Position A, the move `Qg4` might be an instant winning attack because the back rank is vulnerable, whereas in Position B, `Qg4` might lose on the spot because the `h3` pawn gives the king an escape square (`Kh2`) and covers `g4`. This property—often called **tactical chaos** or high sensitivity to initial conditions—means that smooth interpolation in embedding space fails. An LLM cannot rely on "positional vibes" or semantic similarity to similar master games when a one-square shift of a distant pawn completely inverts the game's outcome.

### Verification Loops and Test-Time Filtering

Another major factor explaining recent LLM breakthroughs in mathematics is the tightness of the verification loop during both training and inference.

When solving mathematical or coding problems, model developers employ **Reinforcement Learning with Verifiable Rewards (RLVR)**, best-of-$N$ rejection sampling, and formal proof assistants (such as Lean 4 or Isabelle). When a model generates a candidate proof in Lean, or writes a Python script to test a combinatorial conjecture, a deterministic compiler immediately verifies whether the steps are valid. If a step fails to compile, the model receives an exact error message and can iterate. Even in natural language math, intermediate algebraic steps are explicitly written out on the page, allowing the model's self-attention mechanism to inspect the exact symbolic state at step $k$ before generating step $k+1$.

When an LLM plays raw chess without an external engine or board visualizer, it has no compiler checking its intermediate mental imagery. During its chain-of-thought, if it writes, *"If I play 15. Nd5, Black cannot capture because the e7 pawn is pinned to the king,"* nothing in the text pipeline checks whether the `e7` pawn is *actually* pinned. If a knight is sitting on `e6` blocking the pin, the LLM's faulty premise goes uncorrected, and it plays `15. Nd5` straight into a blunder.

---

## 4. Representation: Tokenization versus Spatial Geometry

The medium in which a problem is presented to a neural network places hard constraints on how efficiently the network can compute over it.

### How Chess Notations Fragment Geometry

Chess is fundamentally a two-dimensional geometric system governed by vector rays (ranks, files, and diagonals) and L-shaped jumps. However, LLMs typically ingest chess through one of two textual formats:

1. **Portable Game Notation (PGN):** A chronological log of moves (`1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6`).
2. **Forsyth-Edwards Notation (FEN):** A compressed rank-by-rank string of the current board (`r1bqkbnr/pp2pppp/2np4/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6`).

Neither format preserves two-dimensional spatial adjacency in a one-dimensional token stream:

* **In PGN**, the current location of any piece is a latent variable that can only be recovered by integrating over the entire token sequence from move 1.
* **In FEN**, horizontal adjacency (along a rank) corresponds to adjacent characters, unless empty squares are compressed into integers like `8` or `3`, which shifts the character offsets of all subsequent pieces on that rank. Vertical adjacency (along a file) and diagonal adjacency require non-constant index arithmetic across slash-delimited substrings.

Furthermore, standard Byte-Pair Encoding (BPE) tokenizers are trained on general web text, not chess grids. A BPE tokenizer might merge `Nf3` into a single token, split `Bxf7+` into `B`, `xf`, `7`, `+`, or chunk segments of a FEN string like `ppp/8/8/PPP` into arbitrary multi-character tokens. This tokenization obscures the underlying coordinate grid before the first transformer layer even processes the input.

### Emergent World Models and Their Limits

Despite the awkwardness of PGN representations, interpretability research has demonstrated that transformers trained on chess games are not merely memorizing surface-level n-gram statistics.

Most notably, research by Toshniwal et al. (2022) and subsequent mechanistic interpretability work by Kenneth Li et al. (on Othello-GPT) and **Adam Karvonen (2024)** (*Emergent World Models and Latent Variable Estimation in Chess-Playing Language Models*) trained GPT-style architectures exclusively on sequences of PGN characters without providing any rules of chess or explicit board grids. By training linear probes on the internal residual stream activations of these models, researchers proved that the networks spontaneously learn to compute an accurate internal representation of the 8x8 board state. Specific directions in activation space reliably encode whether a white bishop currently occupies `c4`, whose turn it is, and which squares are legally accessible. Furthermore, causally intervening on these internal activations—editing the hidden state to erase a piece from a square—causes the model to change its next move prediction to match the modified board state.

Why, then, do general-purpose LLMs still blunder if transformers can learn internal world models?

1. **Capacity Allocation:** Karvonen's models were specialized transformers trained *exclusively* on millions of PGN games to predict the next move. Every attention head and MLP neuron in those models was dedicated to tracking chess state transitions and evaluating positions. In a general-purpose frontier LLM, chess PGNs represent a tiny fraction of a multi-trillion-token pretraining corpus. The model must share its circuit capacity across human languages, programming syntax, scientific literature, and world knowledge.
2. **State Estimation versus Deep Rollouts:** Having a linear probe accurately decode the *current* board state $S_t$ at layer 16 leaves fewer remaining layers to compute multi-step hypothetical rollouts ($S_{t+1}, S_{t+2}, S_{t+3}, \dots$). If the first two-thirds of the transformer's depth are spent simply parsing the PGN history to figure out where the pieces currently sit, only the final few layers remain to evaluate tactical interactions and look ahead.
3. **Out-of-Distribution Fragility:** Internal world models learned from human and engine games rely partly on standard piece trajectories. When a game enters bizarre, non-standard territory (for example, four queens on the board, or a 10x10 board variant, or random Fischer Random starting positions), the latent state tracking degrades rapidly.

### The Scratchpad Experiment: Externalizing the Board State

A telling empirical demonstration of this representational bottleneck occurs when a user changes how an LLM is prompted during a chess game. If an LLM is asked to play purely from a PGN move list, its tactical accuracy drops sharply after move 15. However, if the system prompt instructs the model to **explicitly render the full 8x8 ASCII or Unicode board grid at every turn** (and after every candidate move in its chain-of-thought), its play improves noticeably, even on non-standard board variants.

Why does printing an ASCII grid help? By writing the 2D board state directly into the output tokens, the model converts a **latent state-tracking problem** into an **in-context lookup problem**. Instead of spending network depth reconstructing the current board from 60 historical moves, the model's attention heads can attend directly to the most recently rendered 8x8 grid in the context window. In effect, printing the board acts as external working memory, shifting the model from "blindfold chess" to visual board play.

---

## 5. The Engineering Reality: Compute Economics and Specialization

Beyond architectural theory, there is a pragmatic engineering reason why frontier AI laboratories spend hundreds of millions of dollars training LLMs to win International Mathematical Olympiad (IMO) gold medals and solve PhD-level research problems, while making virtually zero effort to train those same LLMs to beat Stockfish at chess.

### Computational Efficiency by Orders of Magnitude

Consider the computational cost of move generation across architectures:

* **Stockfish 17** running on a single consumer CPU core evaluates roughly 1,000,000 to 2,000,000 nodes per second using a tiny NNUE network (~40 megabytes of weights) and bitwise operations. Within three seconds of wall-clock time on a laptop, it searches tens of millions of positions and plays at a superhuman rating exceeding 3600 Elo.
* **A frontier LLM** (with hundreds of billions of parameters in a Mixture-of-Experts or dense configuration) requires multiple high-end datacenter GPUs (such as NVIDIA H100 or B200 accelerators) consuming kilowatts of power just to generate 50 to 100 text tokens per second.

Even if a lab spent tens of millions of GPU hours training a 500-billion-parameter language model via reinforcement learning to simulate alpha-beta tree search in text tokens, the resulting system would consume millions of times more energy and silicon area per move than a 100-kilobyte C++ binary combined with a compact NNUE weight file, while still playing slower and weaker chess.

### The Economic Value of Generalization

In software engineering and scientific research, no simple algorithmic solver exists. You cannot write a 10,000-line C++ bitwise alpha-beta engine that reads a biology paper, formulates a statistical hypothesis, writes a PyTorch training script, or proves a novel lemma in algebraic geometry. Those domains are unstructured, semantically rich, and expressible only through natural and formal languages. Therefore, investing massive pretraining and reinforcement learning compute into language models for mathematics, coding, and scientific reasoning yields immense economic and scientific return.

Chess, by contrast, is a closed, solved engineering problem from a tool-design standpoint. When an AI agent genuinely needs to evaluate a chess position accurately, the optimal engineering architecture is trivial: equip the LLM with a tool-use function call (`query_stockfish(fen_string, depth=20)`). The LLM handles natural language interaction, pedagogical explanation, and strategic commentary—tasks where Stockfish's raw centipawn output is opaque to human learners—while delegating exact tree search to the deterministic engine.

### What Unassisted LLM Chess Performance Actually Represents

When evaluated fairly, the fact that frontier models (or small specialized transformers trained on PGNs) play chess around the **1600 to 1900 Elo level** without explicit tree search is not an indictment of transformer reasoning; it is a remarkable byproduct of scale and representation learning. A 1700 Elo rating places an unassisted, zero-search language model in the top 5% to 10% of active online human players, playing effectively blindfolded from a string of algebraic coordinates.

---

## 6. Synthesis: Mapping the Boundaries of Transformer Cognition

The contrast between graduate-level mathematical reasoning and chessboard calculation clarifies what large language models actually are—and what they are not.

1. **Transformers are exceptional heuristic priors and semantic synthesizers.** When a problem can be decomposed into high-level conceptual steps, where natural language descriptions guide the selection of theorems, algorithms, or proof structures, and where multiple valid paths lead to the same destination, autoregressive models excel. They compress the collective mathematical intuition of human literature into navigable vector spaces.
2. **Transformers are inefficient deterministic state simulators.** When a problem requires tracking exact, mutable state variables across dozens of sequential steps without an external scratchpad, and where a single coordinate slip invalidates the entire computation, raw next-token prediction struggles.
3. **Linear chain-of-thought is not a substitute for high-branching minimax search.** In domains governed by existential quantifiers ($\exists$), generating a linear chain of reasoning with occasional self-correction is sufficient to discover a valid proof. In adversarial domains governed by alternating quantifiers ($\exists \forall$), where an opponent actively exploits any single unexamined branch, linear token generation cannot compete with dedicated, high-throughput tree search algorithms.

Understanding this boundary prevents two common errors in AI discourse: dismissing LLMs as mere "stochastic parrots" because they blunder a knight in a blitz game, or assuming that scaling laws alone will turn text predictors into optimal solvers for every computational complexity class. Just as human mathematicians use pen, paper, and computer algebra systems rather than multiplying ten-digit matrices in their heads, the future of capable AI systems lies in pairing the broad, associative reasoning of language models with deterministic verifiers, symbolic compilers, and specialized search engines.
