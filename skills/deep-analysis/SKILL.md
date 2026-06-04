---
name: deep-analysis
description: >
  Start a deep analysis session for investigating bugs, performance issues,
  or prototyping algorithms. Creates an isolated workspace, runs experiments,
  and produces a documented handoff — without modifying the main codebase.
  Use when the user asks to investigate, analyze, profile, benchmark, or
  compare approaches in depth.
argument-hint: "[topic to investigate]"
---

# CLAUDE DEEP ANALYSIS PROTOCOL

The topic to investigate: $ARGUMENTS

---

## CRITICAL RULES - READ FIRST

**YOU ARE IN AUTO-ACCEPT MODE. ANY REJECTION = SESSION DEATH = ALL WORK LOST.**

**ABSOLUTELY FORBIDDEN (will cause rejection):**
- Edit/Write to `src/`, `tests/`, or ANY codebase files
- `git commit`, `git push`, `git checkout`, `git reset` (ANY write git operations)
- Delete/rename files outside analysis folder

**MANDATORY:**
- Create `.analysis/analysis_<topic>_YYYY_MM_DD/` folder - ALL work goes here
- Clean up to <=7 TOP-LEVEL items before finishing
- Write comprehensive handoff summary (10-20 sentences, all required sections)

**YOUR JOB:** Investigate -> Document -> Propose -> Handoff. **NOT implement.**

**IF YOU VIOLATE THESE RULES, THE SESSION ENDS AND ALL YOUR WORK IS LOST.**

---

## PURPOSE

This protocol governs deep analysis sessions where thorough investigation, experimentation, and testing are required without modifying the main codebase. Use this when you need to:
- Investigate complex bugs or performance issues
- Analyze data patterns and quality metrics
- Prototype new features or algorithms
- Compare different approaches systematically
- Generate comprehensive reports with evidence

---

## AUTO-ACCEPT MODE - CRITICAL CONTEXT

**THIS PROTOCOL IS DESIGNED FOR AUTO-ACCEPT MODE:**
- All tool uses are automatically accepted without user review
- **ANY REJECTION ENDS THE SESSION IMMEDIATELY**
- **ALL ANALYSIS WORK IS LOST IF SESSION ENDS**
- Therefore: NEVER attempt actions that might be rejected

**The Golden Rule:**
> If there's ANY chance the user might reject an action, DON'T DO IT.

**Session-Ending Actions (FORBIDDEN):**
- Editing codebase files (`src/`, `tests/`, etc.)
- Writing to codebase files
- Git commits (even if changes are good)
- Git push
- Deleting or renaming main codebase files
- Any destructive operations outside analysis folder

**Safe Actions (Unlimited):**
- Reading any files
- Creating files in analysis folder
- Editing files in analysis folder
- Running scripts
- Generating visualizations
- Writing reports
- Cleanup operations in analysis folder

**Remember:** Unfinished deep analysis = garbage. Always complete the full workflow.

---

## CRITICAL RULES - ZERO TOLERANCE

### **RULE 1: ISOLATED WORKSPACE**
- **MANDATORY:** Create a dedicated analysis folder in the current directory
- **Naming:** Use descriptive name: `.analysis/analysis_<topic>_YYYY_MM_DD/` or `.analysis/deep_<issue_name>/`
- **ALL artifacts go here:** scripts, data, plots, logs, intermediate results
- **NEVER** work directly in the current directory during analysis

### **RULE 2: CODEBASE IS READ-ONLY + NO WRITE GIT OPERATIONS**
- **ABSOLUTELY NO modifications** to the main codebase
- **NO edits** to files in `src/`, `tests/`, or any project directories
- **NO write git operations EVER during deep analysis:**
  - `git commit` - FORBIDDEN (risks user rejection -> session death)
  - `git push` - FORBIDDEN
  - `git checkout` - FORBIDDEN (changes working tree)
  - `git reset` - FORBIDDEN
  - `git tag` - FORBIDDEN
  - `git merge` - FORBIDDEN
  - Any git operation that modifies repository state or working tree
  - **Why:** In auto-accept mode, these risk user rejection -> all analysis work lost
- You may:
  - Read any codebase files
  - Import and use existing modules
  - Copy code to analysis folder for experiments
  - Read-only git operations (`git log`, `git diff`, `git status`, `git show`, `git blame`)

### **RULE 3: PROPOSE, DON'T IMPLEMENT**
- If you identify needed changes, create `PROPOSED_CHANGES.md`
- Document:
  - **What** needs to change (specific files, line numbers)
  - **Why** it's necessary (root cause, impact)
  - **How** to implement (exact code changes)
  - **Evidence** supporting the change (test results, metrics)
- **Wait for user approval** before making any codebase changes

### **RULE 4: CLEAN EXIT**
- After analysis, clean up the analysis folder
- **Keep maximum 5-7 essential items:**
  - Final report (markdown)
  - Key visualizations (1-3 plots/figures)
  - Summary data (1-2 CSV files maximum)
  - Proposed changes document (if applicable)
  - Archive folder for intermediate work (optional)
- Move or delete:
  - Debug scripts
  - Test scripts
  - Intermediate data files
  - Failed experiments
  - Temporary outputs

### **RULE 5: COMPREHENSIVE HANDOFF SUMMARY**
- At the end of your analysis, provide a **comprehensive summary** (10-20 sentences, ~1 page)
- This is what the user reads - make it complete and self-contained
- Include:
  - **Context:** What problem was investigated and why
  - **Methodology:** What experiments/analysis were performed
  - **Key Findings:** Main discoveries with quantitative evidence
  - **Root Causes:** Why problems occur (technical details)
  - **Impact Assessment:** How findings affect the codebase/users
  - **Recommendations:** Prioritized action items with justification
  - **Evidence Summary:** Brief mention of supporting data/plots
  - **Location:** Where to find full report and detailed results
- **Format:** Write as a cohesive narrative, not a fill-in-the-blank template
  - Use the sections as a guide, but let it flow naturally
  - Tell the story clearly - what you discovered and why it matters

---

## MANDATORY CHECKPOINTS - STOP AND VERIFY

**BEFORE creating/editing ANY file outside analysis folder:**
```
> STOP. Am I in my analysis folder?
> Check: pwd shows .analysis/analysis_<topic>_YYYY_MM_DD?
> If NO: ABORT. cd into analysis folder first.
```

**BEFORE ANY git operation:**
```
> STOP. Is this a write operation?
> Write ops: commit, push, checkout, reset, merge, tag
> If YES: ABORT. Read-only git operations only (log, diff, status, show, blame).
```

**BEFORE finishing analysis:**
```
> STOP. Checklist time:
  [ ] Analysis folder cleaned to <=7 TOP-LEVEL items?
  [ ] Comprehensive handoff written (10-20 sentences)?
  [ ] All required sections in handoff?
  [ ] Have I committed ANYTHING? (Must be NO)
  [ ] Have I edited ANY codebase files? (Must be NO)
> If ANY checkbox fails: FIX IT before proceeding.
```

---

## DEEP ANALYSIS WORKFLOW

### **Phase 1: Setup (Required)**

```bash
# 1. Create isolated workspace
mkdir -p .analysis/analysis_<topic>_$(date +%Y_%m_%d)
cd .analysis/analysis_<topic>_$(date +%Y_%m_%d)

# 2. Create initial structure
touch ANALYSIS_PLAN.md
touch FINDINGS.md
mkdir -p data plots scripts
```

**Document your plan:**
- What are you investigating?
- What questions need answers?
- What experiments will you run?
- What metrics will you collect?

### **Phase 2: Investigation (Unrestricted)**

You have **COMPLETE FREEDOM** within the analysis folder:

**Create any scripts you want:**
```python
# test_hypothesis_1.py
# debug_performance.py
# compare_algorithms.py
# generate_synthetic_data.py
```

**Modify scripts freely:**
- Iterate rapidly
- Try different approaches
- Break things and fix them
- No need to ask permission

**Run experiments extensively:**
```bash
python test_hypothesis_1.py
python test_hypothesis_2.py --param 0.5
python test_hypothesis_2.py --param 1.0
python test_hypothesis_2.py --param 2.0
```

**Generate artifacts:**
- Plots, charts, visualizations
- CSV files with metrics
- Log files from experiments
- Intermediate data files
- Comparison tables

**Import from main codebase:**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from pipeline.clustering import spectral_cluster
```

### **Phase 3: Documentation (Required)**

Create comprehensive documentation in `FINDINGS.md`:

```markdown
# Deep Analysis: [Topic]

## Executive Summary
[3-5 sentences: what was investigated, key findings, recommendations]

## Investigation Scope
- Questions addressed
- Methods used
- Data analyzed

## Key Findings

### Finding 1: [Title]
**Evidence:** [Plot, metric, or data reference]
**Impact:** [What this means]
**Root Cause:** [Why this happens]

### Finding 2: [Title]
...

## Detailed Results

### Experiment 1: [Name]
- **Setup:** [Parameters, data used]
- **Results:** [Quantitative outcomes]
- **Visualization:** See `plots/experiment1_results.png`

## Recommendations

### High Priority
1. [Action item with justification]

### Medium Priority
...

## Appendix
- Full data: `data/comprehensive_metrics.csv`
- Scripts: `scripts/` directory
```

### **Phase 4: Propose Changes (If Needed)**

If codebase modifications are necessary, create `PROPOSED_CHANGES.md`:

```markdown
# Proposed Changes: [Topic]

## Motivation
[Why these changes are necessary - reference findings]

## Change 1: Fix [Issue] in [File]

**File:** `src/pipeline/clustering.py`
**Lines:** 87-89
**Issue:** [Describe current problem]
**Evidence:** [Reference from FINDINGS.md]

**Current Code:**
adjacency = build_adjacency(graph, method='dense')
labels = spectral_cluster(adjacency, k=k)

**Proposed Fix:**
adjacency = build_adjacency(graph, method='sparse', threshold=0.01)
labels = spectral_cluster(adjacency, k=k, solver='lobpcg')

**Impact:**
- 4.2x speedup on graphs with >10k nodes (142s -> 34s)
- Identical clustering quality: ARI=0.97 vs baseline (see plots/speedup_comparison.png)

**Testing:**
- Verified on 5 synthetic graphs (500-50k nodes, see data/metrics_test.csv)
- No quality regressions observed

## Change 2: ...

---

## Implementation Order
1. Change 1 (critical - fixes accuracy)
2. Change 3 (high priority - performance)
3. Change 2 (nice to have - code clarity)
```

---

### **"But I Need To Test My Proposed Fix!"**

**Problem:** You want to verify your proposed change actually works before recommending it.

**Solution:** Test using modified copies in your analysis folder.

**DO THIS:**
```python
# In analysis_folder/test_fix.py

# Step 1: Copy the file you want to modify to analysis folder
# (Use cp command or Read -> Write)

# Step 2: Modify YOUR COPY (e.g., clustering_modified.py)

# Step 3: Import and test YOUR modified version
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))  # Analysis folder first
from clustering_modified import spectral_cluster  # Your test version

# Step 4: Run experiments with modified version
labels = spectral_cluster(adjacency, k=5, solver='lobpcg')
# ... test your changes ...

# Step 5: Document results in PROPOSED_CHANGES.md
```

**DON'T DO THIS:**
- Edit src/pipeline/clustering.py "just to test"
- "I'll revert it after testing" - NO, session will end if user rejects

**The modified copy strategy:**
- Safe - no codebase changes
- Verifiable - you can prove the fix works
- Documented - test script shows your methodology
- Reproducible - user can run your test script

---

### **Phase 5: Cleanup (Required)**

**Goal:** Reduce to <=7 TOP-LEVEL items in analysis folder.

**What counts as "one item"?**
- Each file = 1 item
- Each folder = 1 item (regardless of contents)

**Typical final structure (4-5 items):**
```
.analysis/analysis_topic_2025_01_15/
├── FINDINGS.md                    # Item 1: Main report
├── PROPOSED_CHANGES.md            # Item 2: Change proposals (if needed)
├── plots/                         # Item 3: Folder with visualizations
│   ├── key_result.png
│   └── comparison.png
├── data/                          # Item 4: Folder with summary data
│   └── metrics_summary.csv
└── archive/                       # Item 5: Optional, all intermediate work
    ├── scripts/
    └── old_data/
```

**Cleanup process:**
```bash
# 1. Create archive for intermediate work
mkdir -p archive

# 2. Move all debug/test scripts
mv scripts/debug_*.py archive/ 2>/dev/null
mv scripts/test_*.py archive/ 2>/dev/null

# 3. Move intermediate data
mv data/intermediate_*.csv archive/ 2>/dev/null
mv data/raw_*.csv archive/ 2>/dev/null

# 4. Keep only best plots (delete or archive rest)
cd plots && ls -t | tail -n +4 | xargs -I {} mv {} ../archive/ 2>/dev/null

# 5. Verify count
cd .. && ls -1 | wc -l
# Should show <=7
```

**If you have 8+ items:**
- You haven't cleaned enough
- Merge similar files into folders
- Archive or delete non-essential items
- Be ruthless - only keep what user needs to see

### **Phase 6: Comprehensive Handoff (Required)**

At the end of your analysis, provide a detailed summary to the user:

---

**DEEP ANALYSIS COMPLETE: [Topic]**

**Context & Motivation:**
[2-3 sentences explaining what problem was investigated and why it matters]

**Investigation Methodology:**
[2-3 sentences describing the experiments performed: data generation, parameter sweeps, metrics collected, etc.]

**Key Findings:**
[3-5 sentences covering main discoveries with quantitative evidence. Include numbers, percentages, comparisons.]

**Root Cause Analysis:**
[2-3 sentences explaining WHY the problems occur - technical details, architecture issues, algorithmic limitations]

**Impact Assessment:**
[2-3 sentences on how these findings affect users, performance, accuracy, or development workflow]

**Recommendations:**
1. **[Priority 1]:** [Action with justification and expected impact]
2. **[Priority 2]:** [Action with justification and expected impact]
3. **[Priority 3]:** [Optional - if applicable]

**Supporting Evidence:**
- Quantitative results: [Brief mention of key metrics/data files]
- Visualizations: [Brief mention of key plots]
- Detailed documentation: `.analysis/analysis_<topic>_YYYY_MM_DD/FINDINGS.md`

---

**Example Handoff:**
> DEEP ANALYSIS COMPLETE: Graph Clustering Pipeline Performance
>
> **Context & Motivation:**
> The clustering pipeline becomes unusably slow on graphs with >10k nodes, taking 140+ seconds where users expect <30s. Profiling was needed to identify bottlenecks and evaluate alternative algorithms without sacrificing clustering quality (ARI).
>
> **Investigation Methodology:**
> Generated 5 synthetic graphs (500, 2k, 10k, 25k, 50k nodes) with known community structure (planted partition model, 5-20 communities). Profiled the current pipeline end-to-end, then benchmarked 4 alternative approaches: sparse adjacency + LOBPCG eigensolver, approximate spectral via Nystrom, Louvain, and leiden. Collected metrics: wall time, peak memory, ARI vs ground truth, and modularity across all graph sizes.
>
> **Key Findings:**
> Found two dominant bottlenecks: (1) `build_adjacency` constructs a dense NxN matrix even though >95% of entries are near-zero for real-world graphs. This alone accounts for 60% of runtime and causes OOM above 50k nodes. (2) The eigensolver uses full decomposition (`numpy.linalg.eigh`) when only k eigenvectors are needed. Switching to sparse adjacency (threshold=0.01) + LOBPCG solver achieved 4.2x speedup at 10k nodes and 11x at 50k nodes, with identical clustering quality (ARI=0.97+-0.01). Louvain was fastest (22x) but dropped ARI to 0.89.
>
> **Root Cause Analysis:**
> The dense adjacency matrix was a reasonable default for small graphs but scales as O(N^2) in memory and time. For sparse real-world graphs (avg degree ~20), >99% of the matrix is zeros. Similarly, computing all N eigenvectors when only k=5-20 are needed wastes O(N^2*k) operations. Both issues stem from the pipeline being written for correctness on small inputs without considering scaling.
>
> **Impact Assessment:**
> Any graph with >5k nodes is significantly affected -- 10k takes 142s (should be ~34s), and 50k either OOMs or takes >20 minutes. The sparse + LOBPCG fix maintains full quality while making the pipeline practical up to ~100k nodes. No API changes are needed -- only internal implementation swaps. All 5 test graphs achieved ARI>0.95 after fixes, compared to identical quality before (the speedup is free).
>
> **Recommendations:**
> 1. **Switch to sparse adjacency with threshold** (HIGH PRIORITY): Eliminates O(N^2) memory. Requires 2 line changes in `clustering.py` (lines 87-89). Expected: 4-11x speedup depending on graph size, no quality loss. See `PROPOSED_CHANGES.md` section 1.
> 2. **Replace eigh with LOBPCG eigensolver** (HIGH PRIORITY): Computes only the k needed eigenvectors. Change in `clustering.py` line 102. Complementary to fix #1 -- together they give the full speedup.
> 3. **Add graph-size adaptive strategy** (MEDIUM): Auto-select dense vs sparse based on N. Useful for backward compatibility with small graphs where dense is marginally faster. See `PROPOSED_CHANGES.md` section 3.
>
> **Supporting Evidence:**
> - Quantitative results: `data/scaling_benchmark.csv` (all 5 graph sizes, 4 algorithms, detailed metrics)
> - Visualizations: `plots/speedup_vs_graph_size.png` (scaling curves for all methods), `plots/quality_vs_speed_tradeoff.png` (ARI vs wall time)
> - Detailed documentation: `.analysis/analysis_clustering_perf_2025_03_10/FINDINGS.md`

---

## BEST PRACTICES

### **Experiment Design**
- Test one variable at a time
- Use synthetic data when possible (ground truth known)
- Compare against baseline/control
- Quantify improvements with metrics
- Visualize results for clarity

### **Evidence Quality**
- **Quantitative:** Use metrics (R^2, MAE, error rates)
- **Visual:** Create clear plots with labels
- **Statistical:** Show mean +- std, sample sizes
- **Reproducible:** Document random seeds, parameters

### **Script Organization**
```
scripts/
├── 1_generate_data.py          # Numbered for workflow
├── 2_run_experiments.py
├── 3_analyze_results.py
├── 4_create_visualizations.py
└── utils.py                    # Shared functions
```

### **Data Management**
```
data/
├── raw/                        # Original data (read-only)
├── processed/                  # Intermediate results
├── results/                    # Final metrics
└── summary_FINAL.csv          # Keep this one after cleanup
```

### **Iterative Development**
- Start simple, add complexity gradually
- Validate each step before proceeding
- Keep a log of what worked/failed
- Don't delete failed experiments until analysis is complete

---

## COMMON PITFALLS TO AVOID

- **Don't modify codebase "just to test something"** - Create test scripts in analysis folder instead
- **Don't leave dozens of files after cleanup** - Archive or delete intermediate work; keep only essential outputs
- **Don't skip documentation** - Future you (and users) need context; "obvious" findings aren't obvious later
- **Don't propose changes without evidence** - Every proposal needs quantitative support; show before/after comparisons
- **Don't forget the handoff summary** - User needs concise actionable summary; point to full report for details

---

## PROTOCOL CHECKLIST

Before completing your analysis, verify:

- [ ] All work is in isolated analysis folder
- [ ] Zero modifications to main codebase
- [ ] NO git commits attempted (session-ending action)
- [ ] FINDINGS.md documents investigation thoroughly
- [ ] PROPOSED_CHANGES.md exists (if changes needed)
- [ ] Evidence supports all claims (metrics, plots)
- [ ] Analysis folder cleaned to <=7 essential items
- [ ] Comprehensive handoff summary provided (10-20 sentences)
- [ ] Handoff includes: context, methodology, findings, root causes, impact, recommendations
- [ ] User knows where to find full report
- [ ] Recommended actions are clear, specific, and prioritized

---

## EXITING DEEP ANALYSIS MODE

**Your analysis is complete when:**
- All phases of the workflow are finished
- Comprehensive handoff summary is written
- Analysis folder is cleaned and organized
- User has all information needed to take action

**The user will then decide:**
- Whether to implement proposed changes
- When to apply fixes (immediately or later)
- Whether additional analysis is needed

**NEVER attempt to implement changes yourself during deep analysis.**
**NEVER commit anything during deep analysis.**

If user asks you to implement changes, that begins a NEW session following CLAUDE.md protocol (not this protocol).

---

## EXAMPLE SESSION

```
User: "Investigate why graph clustering is slow on large inputs"

You (Deep Analysis Mode):
1. Create .analysis/analysis_clustering_perf_2025_03_10/
2. Generate synthetic graphs at various sizes (500-50k nodes)
3. Profile the pipeline end-to-end, benchmark alternative algorithms
4. Collect metrics (wall time, memory, ARI), create visualizations
5. Identify root causes: dense adjacency matrix + full eigendecomposition
6. Document findings in FINDINGS.md
7. Propose fix in PROPOSED_CHANGES.md
8. Clean up (archive debug scripts, keep 5 key files)
9. Provide comprehensive handoff summary (10-20 sentences)
10. DONE - Deep analysis complete, no commits made

Your job ends here. User will handle implementation in a separate session if desired.
```

---

## SUCCESS CRITERIA

Your deep analysis is successful when:
- Problem is understood at root cause level
- Evidence is quantitative and reproducible
- Findings are clearly documented
- Recommendations are actionable and prioritized
- Main codebase remains unchanged (until approved)
- Analysis folder is clean and organized
- User can quickly understand results and take action

---

**Remember:** Deep analysis mode gives you freedom to experiment extensively, but with great freedom comes great responsibility to document, organize, and clean up properly. The goal is to emerge with clear insights and actionable recommendations, not a mess of scattered experiments.

---

## QUICK REFERENCE CARD

**Session-Killing Actions (NEVER DO):**
```
Edit src/, tests/, or any codebase file
git commit / git push / git checkout / git reset
Delete/rename codebase files
```

**Safe Actions (Do Freely):**
```
Read any files, git log/diff/status
Create/edit files in analysis folder
Run experiments, generate plots
Write reports and proposals
```

**Your Workflow:**
```
1. mkdir -p .analysis/analysis_<topic>_$(date +%Y_%m_%d) && cd into it
2. Experiment freely within this folder
3. Document in FINDINGS.md
4. Propose changes in PROPOSED_CHANGES.md (if needed)
5. Clean to <=7 items (archive the rest)
6. Write 10-20 sentence comprehensive handoff
7. Done - no commits, no codebase changes
```

**Before Finishing - Final Checks:**
```
[ ] In analysis folder? (ls -1 | wc -l shows <=7)
[ ] FINDINGS.md exists and complete?
[ ] PROPOSED_CHANGES.md if needed?
[ ] Comprehensive handoff written?
[ ] Zero commits made?
[ ] Zero codebase edits?
```

**If you violated any rule -> Session ends -> All work lost**
