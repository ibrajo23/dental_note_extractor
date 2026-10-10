# Dental Note Extractor

I'm a dentist learning Python. I built this small project to see how well simple code can turn messy dental notes into structured data, and later to compare it with an AI model (LLM).

**Status:** work in progress. Tooth number extraction is done with rules and with an LLM, and compared. Diagnosis and procedure extraction is next.

## The problem

Dentists write notes in a hurry, in their own shorthand:

```
class 2 restoration for reversible pulpitis tooth number #45
UR6 deep distal caries RCT started
pulpotomy for upper right d and lower right e and place scc on both of them
```

A computer system needs structured data: which tooth, what diagnosis, what procedure. The first step is finding the tooth number, and that is harder than it looks.

## Why finding the tooth is hard

- **Several numbering systems get mixed.** FDI (36), Universal (#19), words ("lower right first molar"), shorthand ("UR6", "lower right 6") and letters for baby teeth ("upper right d").
- **Many numbers are valid in more than one system.** 11-18, 21-28, 31 and 32 exist in both FDI and Universal, so the digits alone don't tell you the system. My code assumes FDI.
- **Other numbers look like teeth.** "class 2", "stage 3", "8 year old", "MB2 canal", "lidocaine 2% 1.8 ml".
- **Notes have several teeth, or none.** "heavy calculus on #31 and #32 and #41, #42", "full mouth scaling".

## What I built

- `notes.txt`: 149 fictional dental notes in my own shorthand. **No real patient data.**
- `answers.txt`: my answer key, one line per note: `tooth | system | diagnosis | procedure`. The tooth is always stored as FDI.
- `main.py`: rule-based Python (regex and lookup tables) that finds the tooth numbers and scores them against my answer key.

## Results: rule-based tooth number extraction

I tuned the rules on my first notes, so a score on those only shows that the rules fit them. The honest number is the one on notes the rules had never seen.

| Notes | Result |
|---|---|
| First 27 notes (rules tuned on these) | 27/27 |
| Unseen notes, all sets combined (122 notes, each scored before I fixed anything) | 99/122 (81%) |

Unseen sets, each scored before I fixed any failure:

| Set | Notes | Correct |
|---|---|---|
| Batch 1 | 10 | 5 |
| Batch 2 | 50 | 45 |
| Letter notation for baby teeth | 2 | 0 |
| Batch 3 | 20 | 15 |
| Batch 4 | 20 | 17 |
| Batch 5 (never fixed afterwards) | 20 | 17 |

After I fixed the failures in batches 1-4, the rules score 146/149 on all my notes. The three misses are batch 5, which I did not fix on purpose. That number is optimistic, because I wrote the fixes after seeing those exact notes. The honest result is the 99/122 above.

### Where the rules failed (before I fixed them)

- Shorthand written in a new way: "UR6", "L upper 7"
- Numbers that are not teeth: ages, doses ("lidocaine 2% 1.8 ml"), "MB2", "class 2"
- Words between the tooth words: "lower left second **primary** molar"
- Two jaw and side phrases in one note: "upper right and lower right third molars"
- Letters for baby teeth: "upper right d"

### Still not handled

- "upper right and left canines" returns only the upper right one
- "lower 6" with no side, and a number after the tooth that is not a tooth: "lower left 6 3 times a day"
- Number written before the jaw and side ("8 lower right"), and a baby-tooth letter before them ("E lower right")
- A whole quadrant ("upper right quadrant")
- Lone "A" for the baby central incisor is not read, because it looks like the word "a"

Every fix makes the code longer and more fragile, and a clinician can always write something new. That is why I compared the rules with an LLM.

## Results: rules vs LLM (tooth number)

I sent the same 149 notes to an LLM (Claude Sonnet 5.5) with a short instruction that describes the task and the conventions in my answer key. The instruction is in `llm_compare.py`. The replies were scored with the same scorer as the rules.

| Notes | Rules | LLM |
|---|---|---|
| First 37 | 37/37 | 37/37 |
| Batch 2 (50 notes) | 50/50 | 48/50 |
| Letter notation (2 notes) | 2/2 | 2/2 |
| Batch 3 (20 notes) | 20/20 | 18/20 |
| Batch 4 (20 notes) | 20/20 | 20/20 |
| Batch 5 (20 notes, rules never fixed) | 17/20 | 20/20 |
| All 149 | 146/149 | 145/149 |

**How to read this.** The rules were fixed after I saw every batch except the last, so only batch 5 is a fair comparison. The LLM was never adjusted to any of my notes. Batch 5 is only 20 notes, and each side was run once, so this suggests a difference but does not prove one. The LLM instruction also tells it my conventions (for example, baby-tooth letters a to e), and two of its examples ("upper right d", "upper right quadrant") came from my own notes, which probably helped it on batch 5.

### What the mistakes looked like

- **Rules fail quietly when the wording is unusual.** They returned nothing or a wrong number for "8 lower right", "E lower right" and "upper right quadrant". The LLM got all three right.
- **The LLM fails by listing too many teeth.** For "toothache lower left side, patient could not point exact tooth" it listed all eight lower left teeth. For "upper arch complete denture try in" it listed all 16 upper teeth, on a patient who may have none. In a clinic, a confident wrong tooth is worse than an empty answer.
- **Two LLM answers are debatable, not clearly wrong.** For "extraction of 44" in a note that also mentions the canine, it returned 43 and 44. For "extraction of retained deciduous 53 canine, permanent canine erupting palatally" it returned 13 and 53. My key lists only the tooth that was treated. I have not changed the key to fit the LLM's answers.

## What I decided as a clinician

- Store every tooth as FDI in the answer key, and convert from other systems.
- When the side is missing ("lower d"), the key lists both possible teeth.
- "none" means no procedure was done, and "not stated" means the note gives no diagnosis. They are different.
- Keep the answer key's vocabulary fixed (e.g. always `root canal treatment`, `extraction`) so results can be compared.

## Next steps

1. Extract diagnosis and procedure, not only the tooth, and compare rules and LLM again.
2. Test an improved LLM instruction (for example, "a side or arch alone is not a tooth") on a fresh set of notes, and report both versions.
3. Add a safety check: flag notes where the LLM lists many teeth for a human to review.

## How to run

```
python main.py            # rules only
python llm_compare.py     # rules vs LLM
```

Needs Python 3. Put `notes.txt` and `answers.txt` in the same folder. For `llm_compare.py` you also need `pip install anthropic` and an API key in the environment variable `ANTHROPIC_API_KEY`. Never put the key in a file.

## About how I built this

I'm a beginner in Python. I used Claude to help me write and debug the code and to generate some of the test notes and answers. The clinical decisions, the first notes, the answer-key rules and the review of the results are mine. [Edit this line to say exactly what you checked yourself.]

## Limits

This is a learning project on fictional notes. It is not a medical device and must not be used with real patient records.