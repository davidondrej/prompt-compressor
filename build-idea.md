<idea>
prompt compressor

taking very long prompts, like 7000 lines, aka 75k tokens

and compressing them by a set %, such as 35%, without losing essential context
</idea>


<problem>
the fact that when i just tried this, with GPT-5-high, that has 400k context window, and told it very clearly what i want, and to achieve a 30% length reduction, it managed to turn 7000 lines into 266 lines

which is more like 96% reduction
</problem>


<approach>
you cannot do this in one shot.

you have to first split the long prompt into chunks, rate each chunk in terms of relevance, and then run an LLM on each chunk separately, one by one, starting with the least-relevant chunks

and constnatly checking the total token count against the desired length the user provided
</approach>


<research>
Of course. To get started on building the Prompt Compressor tool, a good first step is to research existing techniques and algorithms for prompt compression. I'll look into that for you.
Based on the research, prompt compression techniques can be categorized into two main groups: Hard Prompt Methods (like token pruning, keyword extraction, and summarization) and Soft Prompt Methods (like embedding compression and prompt tuning).

To get you started, I've broken down the project into a checklist and added it to the task description. Here's the plan:

- [ ] Research and select the most suitable compression algorithm.
- [ ] Develop the core compression logic in Python.
- [ ] Build a simple command-line interface (CLI) or a basic web interface to interact with the tool.
- [ ] Test the tool with various prompts and LLMs to evaluate its performance and compression ratio.
- [ ] Refine the algorithm and the tool based on the test results.

I've updated the task with this plan. You can start with the first item on the list: researching and selecting a compression algorithm. Let me know how you'd like to proceed.
Based on my research, prompt compression techniques fall into two main categories:

1.  **Hard Prompt Methods**: These involve removing or condensing parts of the prompt text, such as token pruning, keyword extraction, or summarization.
2.  **Soft Prompt Methods**: These are more advanced and involve working with the underlying data representations, like embedding compression or prompt tuning.

To help you get started, I've added a checklist to the task with the following steps:

*   [ ] Research and select the most suitable compression algorithm.
*   [ ] Develop the core compression logic in Python.
*   [ ] Build a simple command-line interface (CLI) or a basic web interface to interact with the tool.
*   [ ] Test the tool with various prompts and LLMs to evaluate its performance and compression ratio.
*   [ ] Refine the algorithm and the tool based on the test results.

You can now begin with the first step: researching and selecting the most suitable compression algorithm for your needs.
</research>


Six-step implementation plan
1. Chunk: Split Markdown into chunks (respect code fences/headings/lists); record stable IDs and token counts.

2. Rate: Use GPT-4.1 to score each chunk’s relevance (0–10) to preserving intent; lower = safer to compress.

3. Target: Compute global token target from desired reduction (tiktoken); track current total.

4. Compress Loop: While current > target, pick the least-relevant largest chunk and ask GPT-4.1 to shorten it modestly within a per-chunk budget, preserving structure and meaning.

5. Recount: Replace the chunk, recompute tokens, repeat from least-relevant; stop when target met or no safe reductions remain.

6. Output: Stitch chunks in order and write the result; emit simple stats (original/target/final tokens, iterations).
