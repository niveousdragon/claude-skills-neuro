# Paper map format

A map is a YAML file beside the manuscript. Every claim that can be wrong on its own is a node; each
node is tied to three things:
- its places in the text, through anchors in an anchored copy of the LaTeX source;
- what it comes from: files pinned by sha256, code by commit and path, the parameters it was computed with;
- what rests on it.

`paper_map.py` (next to this file; Python 3 with `pyyaml`) checks these ties and answers questions:

```
python paper_map.py place-anchors MAP.yaml            write the anchored copy of the paper from the original
python paper_map.py check MAP.yaml --out R.txt        check the map; exit code 0 when it is clean
python paper_map.py argument MAP.yaml --lang ru       the page for the author: main claims, verdicts, what breaks them
python paper_map.py impact MAP.yaml ID [ID ...]       what a change of these nodes touches, by action, with lines
python paper_map.py trace MAP.yaml ID                 what a node rests on, down to files and code
python paper_map.py strip IN.tex OUT.tex              remove the anchors (a copy for co-authors)
```

## The file

```yaml
paper:
  original: 'paper.tex'                  # the manuscript without anchors, while the anchored copy is not the working text
  file: 'paper_anchored.tex'             # written by place-anchors
  version: '1.0'
  date: 2026-01-15                       # date of this version: sources modified later are flagged
  code_repo: 'path/to/git/repository'    # for sources given as commit + path
  coverage_exclude: ['Acknowledgments', 'Author contributions', 'Competing interests', 'Ethics']
                                         # sections left out on purpose; check reads to \end{document}, the appendix included

scopes:                                  # what a number was computed on, one line each
  S_all: 'all cells, 12 sessions of 5 mice'
  S_m3: 'mouse 3, session 1, 412 cells'

parts: ['parts/fig2.yaml', 'parts/methods.yaml']   # optional: more nodes, scopes and skips, one file per helper

skip:                                    # paragraphs that claim nothing about the work
  - {quote: 'exact quote from the paragraph', why: 'acknowledgment of a grant number'}

nodes:
  - ...
```

Paths are relative to the folder of the main map file, in parts too.

## Nodes

A node is a claim that can turn out wrong independently of its neighbours. Kinds (`kind`):

| kind | what it is |
|---|---|
| `dna` | a main claim of the paper |
| `result` | one measurement or observation, with a number or without |
| `statement` | a claim in Results without a number of its own: "the largest group", "rarely", "the treatment leaves firing rates unchanged" |
| `method` | a processing step, a run, an analysis |
| `param` | a parameter that steps and results depend on: a threshold, a window, a count of shuffles, a rate, a size |
| `assumption` | an assumption that changes the meaning of everything below it |
| `intro` | a question or claim of the Introduction; a question has `question: true` and `answered_by` |
| `discussion` | a position of the Discussion |
| `cite` | a claim about someone else's work; field `bibkey` |

Fields:

| field | meaning |
|---|---|
| `id` | short, no spaces: `R-resp-frac`, `P-thr`, `D-dense` |
| `claim` | what is claimed, one sentence |
| `value` | only this node's numbers: value and interval, `'34 [29, 39]'`; one unit per node, percentages as percent |
| `scope` | a scope from `scopes`: what it was actually computed on |
| `sources` | where the value comes from (below) |
| `uses` | ids of what the value is computed with: parameters, steps, other results |
| `supports` | what rests on this node (below) |
| `checks` | values that must agree with this node's value (below); not dependencies |
| `answered_by` | for a question of the Introduction: the results that answer it |
| `relates` | how this node stands to cited work (below) |
| `confirmed` | for a main claim: the author's agreement, `'2026-01-15, author'`; absent = a proposal |
| `restates`, `adds` | for a Discussion node that restates a main claim: its id, and what the restatement adds |
| `same_measure_as` | the same quantity on another scope |
| `distinct_from` | for a parameter: parameters set on the same line of a source to the same value that are different parameters (`folds=5, shuffles=5`) |
| `mentions` | every place the node is named (below) |
| `decision` | the author's decision about the node: `{date, by, what, why}` |
| `note` | anything else; numbers that are not the node's value go only here |

### `uses`: the counterfactual rule, confirmed in code

If this parameter, file or result changed, would this value change? Then it is in `uses`, whether or not
the text names it nearby. Answer from the code path that produced the value (the script, the library
function it calls, the run's saved parameters), not from what seems plausible: a link the code does not
have sends `impact` to places the change does not touch.

Three cases are missed most often:
- **Runs.** An analysis run (one call of a pipeline with its settings: a batch over sessions, the
  computation inside a figure script) is a `method` node that `uses` every parameter the run was called
  with, the defaults it took included. Each result computed from the run `uses` the run node; it adds only
  what comes after the run, such as its own selection. Lists of parameters written result by result drop
  some, and a change of a dropped parameter then misses those results.
- **Unit conversions.** A quantity stated in physical units that the code converts with another
  parameter `uses` that parameter: a distance in micrometres converted to pixels uses the pixel size, a
  duration in seconds converted to samples uses the sampling rate. So do the library defaults stated in
  physical units in Methods (they use the rate of each dataset they are applied to), and every axis,
  colour bar or duration a figure shows in physical units.
- **Parameters the text never names**: a selection threshold applied before a figure, a library default,
  a constant inside a figure script.

One quantity is one node in the whole map, parts included: the rate of a dataset used by three figures
is one `param` node that all three runs use.

## Sources

```yaml
sources:
  - {file: 'out/resp.csv', sha256: '<sha256 of the file>', locator: 'column frac, row 3', value: '34.2 [29.1, 39.0]',
     how: 'python analysis/resp.py --mouse all'}
  - {commit: 'a1b2c3d4', path: 'src/pkg/stats.py', locator: 'line 88: THRESHOLD = 0.01', value: '0.01'}
  - {commit: 'a1b2c3d4', path: 'src/pkg/mi.py', locator: 'line 40', disagrees: 'uses the KSG estimator; the text says a classifier'}
  - {unavailable: 'library outside the allowed folders', locator: 'pkg/filters.py, line 12', value: '0.5'}
```

- A file always carries its `sha256`. `check` recomputes it every time: a changed file marks the node
  STALE and everything downstream of it RE-CHECK.
- Code is given by commit and path; `locator` names the line.
- `value` holds only the numbers the source gives for this node: the value, and its interval in brackets
  if the node has one. Every number in it is compared with the node, so an explanation (`SE 0.053`,
  `Fig. 4 left`) goes to `locator`; left in `value`, it reads as a CONFLICT. Sources that disagree with
  the node are a finding (CONFLICT); write them down as they are.
- `disagrees`: a disagreement that is not a number, in words: the code uses another estimator, other
  sessions, the training set where the text says the test set. A finding (CONFLICT), shown on the
  argument page under every main claim the node supports.
- `unavailable`: a place that sets the value but cannot be opened (a library outside the allowed folders,
  data on another machine), with the reason; `locator` and `value` as usual. Nothing is pinned or dated;
  `impact` lists it with the other places; a result whose sources are all unavailable is UNSOURCED, with
  the reason.
- `how` says how to get the value again; if it cannot be done, say why.

**A parameter lists every place whose value reaches a result**: the default where nothing overrides it,
each script or config that overrides it, each literal written into code that uses it (`rate = 25`, a
`/ 25.0` in a plotting function), the saved parameters of each run. One `param` node, many sources, each
with its `value`. `impact` prints them under the changed node: these are the places a change has to reach
before a re-run means anything. A default that every run overrides reaches nothing: it is not a source,
write it in `note`. A script that hard-codes a value different from the one the analysis used is a
CONFLICT, which is what it is.

## Mentions

```yaml
mentions:
  - {anchor: resp-abs, quote: 'about 34\% of V1 neurons respond', states: '34', scope: S_all, role: 'main result'}
  - {anchor: resp-res, quote: '34\% (95\% CI 29--39\%) of neurons', scope: S_all}
  - {figure: 'fig2.pdf', panel: 'C', states: '41', scope: S_m3, shows: 'bar for mouse 3'}
```

- `anchor`: the anchor's name, unique in the whole map. `place-anchors` puts it into the text; do not edit
  anchors by hand.
- `quote`: an exact quote from the LaTeX source, with every `\%`, `~`, `{\sim}`. Whitespace and line breaks
  do not matter. The quote must occur once in the manuscript; otherwise lengthen it or add `near_line`.
- `states`: which numbers of this place belong to the node. Without it, all numbers of the quote are taken.
  How numbers are read:
  - `10{,}000`, `10\,000` and `10,000` are one number; so are `6.6\times10^{-11}` and `10^{-3}`;
  - not numbers: the level of an interval ("95% CI", `95\%$ CI`, `95\%~CI`), sub- and superscripts
    (`\theta_1`, `R^2`), names with digits (CA1, F28_1D, L3.1, S6.5, `d_obj1..4`, citation keys), digits
    glued to letters (2D);
  - the digits of a quote are read without signs: a dash is usually a range (`29--39`).
  A number the reading sets aside can still be given in `states` on purpose (the level of an interval as
  a parameter's value).
- `bound: '<'` (or `'<='`, `'>'`, `'>='`): the text gives a bound on a result, not its value ("p < 0.001");
  `check` verifies that the node's value, with its sign, lies on that side. A negative bound is written
  in `states` with its sign (`states: '-0.1'`). For a threshold parameter, the number in "p < 0.001" is
  the parameter's value: use `states`, not `bound`.
- `verbal: true`: the number is written in words ("twenty-eight"). Give it in `states` as digits; `check`
  compares it with the value and does not look for the digits in the quote.
- `scope`: the scope the text claims at this place. Different from the node's `scope`: a finding (SCOPE).
- A figure panel is a mention with `figure` and `panel` and no anchor. `states` holds the numbers printed on
  the panel; `shows` describes what the panel shows (not number-checked).

Every place counts: the Abstract, each Results sentence, the figure caption, the panel itself, the
Discussion repeating the number, the Methods restating a parameter. A sentence that carries two claims
gives each its mention: a claim asserted in passing inside another result's sentence is a mention of its
own node, anchored on the same sentence.

## What rests on a node: `supports`

```yaml
supports:
  - {to: D-dense, says: 'the dense-code argument needs a sizeable responding fraction',
     holds_while: {op: '>=', value: 25}}
  - {to: S-third, says: '"about a third" of the cells respond', holds_while: [{op: '>=', value: 28}, {op: '<=', value: 38}]}
  - {to: S-above-ctrl, says: 'more cells respond than with shuffled stimulus labels', holds_while: {op: '>', node: R-resp-ctrl, margin: 5}}
```

`says` is the link in words. `holds_while` is the condition on this node's value under which the link
holds: compared with a number, or with another node's value plus `margin`; a list of conditions must all
hold. Put one wherever the condition is a number: `check` then reports when a conclusion stops holding
(BROKEN).

A quantity in words ("most", "a third", "nearly all") is its own `statement` node, supported by the numeric
result with `holds_while`: "most" is `{op: '>', value: 50}`, "a third" is a list of two conditions.

## The argument: main claims, components, restatements, literature

The main claims (`dna`) are the author's: an agent proposes them, the author confirms them, and only then
do they carry `confirmed`. A broad claim rests on many demonstrations; give it components (`statement`
nodes that support it), and attach each demonstration to the component it shows:

```yaml
- id: DNA-tool
  kind: dna
  claim: 'the pipeline gives comparable answers on simulated and recorded data'
  confirmed: '2026-01-15, author'
- id: S-tool-sim
  kind: statement
  claim: 'on simulated data with known ground truth, the pipeline recovers what was planted'
  supports: [{to: DNA-tool, says: 'first component: recovery of known truth'}]
- id: R-recovery-f1
  kind: result
  claim: 'F1 of recovering planted cell-variable pairs'
  value: '0.97'
  supports: [{to: S-tool-sim, says: 'recovery is near complete', holds_while: {op: '>=', value: 0.9}}]
```

Every result and statement should reach a main claim through `supports`; `check` lists those that do not,
and the argument page puts them to the author.

A restatement of a main claim that adds something is its own Discussion node; without support of its own
for the addition, `check` reports it as OVERSTATED:

```yaml
- id: D-everywhere
  kind: discussion
  claim: 'the pipeline is routine for any recording substrate'
  restates: DNA-tool
  adds: 'any substrate'
```

How a claim stands to prior work, on results, statements, Discussion and Introduction nodes:

```yaml
relates:
  - {cite: C-smith2020, how: confirms, says: 'same fraction of responsive cells in V1'}
  - {cite: C-lee2021, how: contrasts, says: 'they report sparse coding in the same area'}
```

`how` is one of `confirms`, `extends`, `contradicts`, `contrasts`, `uses`, `motivates`; `cite` is a `cite`
node. The main thoughts of the Discussion should rest on a main claim or a component and carry `relates`.
A position counts as tied to a main claim when it rests on the claim or on a node that argues for it, or
argues for it itself, directly or through a component. A caveat or a limitation is linked to every claim
it limits (`supports` from each claim to the caveat), so that a change of any of them reaches it.

## Values that must agree: `checks`

```yaml
- id: P-pix
  kind: param
  value: '0.5'
  checks:
    - {says: 'the pixel size used in the analysis equals the microscope calibration', holds_while: {op: '==', node: P-calib}}
```

A check is a condition between two values that must agree, not a dependency: neither is computed from the
other. `check` evaluates it (INCONSISTENT when it fails); `impact` names it under the changed node and does
not follow it. Written as `supports` instead, such a condition makes `impact` walk from one value into
everything that depends on the other.

`op: '=='` means agreement at the stated precision (`0.5` and `0.50` agree, `0.5` and `0.6` do not), or
within `tolerance` if one is given.

## `skip`

Only for paragraphs that claim nothing about the work: an acknowledgment, a grant number, an ethics
approval repeated from its own section. A statement of data or code availability is a claim (that these
files exist and will be released): map it. `impact` lists the skipped paragraphs as not analysed.

## What `check` reports

The map is **clean** when there are no integrity errors and no prose paragraph without an anchor. The
whole document is read, the appendix after the references included; the list of references and
definitions of counters and commands are not prose. Findings are for the author, not errors of the map:

| finding | meaning |
|---|---|
| MISMATCH | a number in the text differs from the node's value |
| SCOPE | the text claims a different scope from the one computed on |
| CONFLICT | a source disagrees with the node: a number in its `value`, or the words in `disagrees` |
| STALE | a source file changed since it was pinned; RE-CHECK lists what depends on it |
| AFTER-VERSION | a source was modified after the paper's version date |
| BROKEN | a `supports` condition does not hold |
| INCONSISTENT | a `checks` condition does not hold |
| OVERSTATED | a restatement adds to a main claim with no support of its own |
| UNSOURCED | a result without a source that can be checked (all `unavailable`: with the reason) |

The ARGUMENT section, also for the author: main claims not yet confirmed; results and statements that
serve no main claim; Discussion positions tied to neither a main claim nor the literature; questions of the
Introduction without an answer. It does not make the map unclean.

It also lists, paragraph by paragraph, the numbers outside the quote of every mention anchored there: in
the Abstract, Results, Discussion and captions each is a missed mention, or not a claim at all (a figure
number, a stage named by a number). And warnings: a parameter without a source, two parameters set on the
same line of a source to the same value (usually one parameter written down twice; different parameters
say so in `distinct_from`, never by dropping a true source), a `supports` into a parameter or method
(usually a check written as support), a result's mention without the scope it claims.

## What `impact` reports

Under the changed nodes, where their values are set (sources) and the checks to re-evaluate. Then
everything downstream, by what has to be done:

| tier | what is in it |
|---|---|
| MAIN CLAIMS AT STAKE | the main claims the change reaches, with the state of each support into them; they go to the author, never reworded without agreement |
| RECOMPUTE | results computed from the change through `uses`: numbers and panels |
| REWRITE | methods and parameters that use the changed node directly: their descriptions |
| RE-READ | statements one `supports`, `answers`, `relates` or restatement step away from a changed value, and every statement or Discussion position further up that the change reaches without passing through a main claim: the conclusions of a section and the Discussion drawn from the changed result |
| FURTHER UP | what the change reaches only through a main claim (restatements, the framing of the paper), cited works, and the questions of the Introduction |
| DOWNSTREAM STEPS | methods and parameters fed indirectly: results below them change, their own text probably stands |
| NOT IN THE TEXT | runs, intermediate results and code on the way, with their sources |

The summary gives the lines to look at (recompute, rewrite, re-read), the lines also reached, and the
paragraphs not analysed. `impact` proposes; each place is confirmed against the code before it is edited or
dropped.

## What `argument` writes

The page the author reads first, in English or Russian (`--lang ru` translates the frame; claims appear as
written in the map): for each main claim, whether the author confirmed it, a verdict (holds; does not hold
as written; holds but conditions fail inside its support; rests on so many supports with no checkable
condition; rests on a single support), what breaks it, what the data say against its support, what it
rests on, its restatements, the Discussion and literature around it (tied directly or through a
component), and its places in the text. The verdict is read from the paper's own numbers and conditions;
the findings against the data (CONFLICT, SCOPE, UNSOURCED, MISMATCH anywhere below the claim) are counted
in it and listed under it. Then the questions only the author can answer: unconfirmed main claims, results
in the text that serve no main claim, Discussion positions without a main claim or literature, unanswered
questions of the Introduction.

## Example

```yaml
- id: P-annulus
  kind: param
  claim: 'outer radius of the neuropil annulus, in micrometres; converted to pixels with the pixel size'
  value: '15'
  uses: [P-pix]
  sources:
    - {commit: 'a1b2c3d4', path: 'analysis/extract.py', locator: 'line 12: ANNULUS_UM = 15', value: '15'}
    - {commit: 'a1b2c3d4', path: 'figures/fig2.py', locator: 'line 40: annulus = 15', value: '15'}
  mentions: [{anchor: annulus-m, quote: 'an annulus of 15~$\mu$m around each cell', states: '15'}]
- id: R-resp-frac
  kind: result
  claim: 'fraction of V1 cells responding significantly to gratings'
  value: '34.2 [29.1, 39.0]'
  scope: S_all
  uses: [P-annulus, M-resp-test]
  sources: [{file: 'out/resp.csv', sha256: '...', locator: 'frac', value: '34.2 [29.1, 39.0]', how: 'python analysis/resp.py'}]
  mentions:
    - {anchor: resp-abs, quote: 'about 34\% of V1 neurons respond', states: '34', scope: S_all}
  supports:
    - {to: D-dense, says: 'a sizeable fraction responds', holds_while: {op: '>=', value: 25}}
```
