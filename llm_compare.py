"""Compare my rule-based tooth finder (main.py) with an LLM on the same notes.

Before running:
  1. pip install anthropic
  2. Set your API key as an environment variable (never write it in this file):
       Windows (PowerShell):  $env:ANTHROPIC_API_KEY = "your-key-here"
       Mac/Linux:             export ANTHROPIC_API_KEY="your-key-here"
  3. Run: python llm_compare.py

The LLM's replies are saved in llm_cache.json, so running the script again
does not call the API (and does not cost money) for notes it already did.
Delete llm_cache.json if you change the prompt or the model.
"""
import json
import os
import re

import anthropic

from main import find_teeth  # my rule-based code

# ---------- Settings you may change ----------
MODEL = "claude-sonnet-5-5"          # a cheaper option: "claude-haiku-4-5-20251001"
NOTES_FILE = "notes.txt"
ANSWERS_FILE = "answers.txt"
CACHE_FILE = "llm_cache.json"

# The notes file is in this order. Edit the sizes if your file is ordered
# differently (the sizes must add up to the number of notes).
GROUPS = [
    ("first 37 notes (rules tuned on these)", 37),
    ("50 notes, set 2", 50),
    ("2 letter-notation notes", 2),
    ("20 fresh notes, set 3", 20),
    ("20 fresh notes, set 4", 20),
    ("20 fresh notes, set 5", 20),
]

# The same rules my answer key follows. The LLM gets exactly this, so the
# comparison is fair: it knows the task and the conventions, nothing more.
SYSTEM_PROMPT = """You read one short dental clinic note and list the tooth numbers it is about.

Rules:
- If the note writes tooth numbers as digits (e.g. 36, #14, tooth 8), return them exactly as written. Do not convert between numbering systems.
- If the note names a tooth in words (e.g. "lower right first molar"), as shorthand (e.g. "UR6", "lower right 6"), or with a baby-tooth letter (e.g. "upper right d"), return the FDI number.
- Baby (primary) teeth in FDI are 51-55, 61-65, 71-75, 81-85. Letters for baby teeth: a=1 (central incisor) to e=5 (second molar), given with jaw and side, e.g. "upper right d" = 54.
- If a note names a group (e.g. "lower incisors", "upper right quadrant") list every FDI tooth in it.
- If the side is not given, include both sides.
- Ignore numbers that are not teeth: ages, doses, measurements, classes, grades, stages, shades, dates.
- If the note names no tooth at all, return an empty list.

Reply with only JSON, like: {"teeth": ["36", "37"]}"""


def ask_llm(client, note):
    """Send one note to the model and return its raw text reply."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,  # room for the model's thinking plus the short answer
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": note}],
    )
    # The reply can contain several blocks (for example a "thinking" block
    # before the answer). We only want the blocks that are plain text.
    texts = [block.text for block in response.content
             if getattr(block, "type", "text") == "text"]
    return "\n".join(texts)


def parse_teeth(reply):
    """Turn the model's JSON reply into a sorted list of tooth numbers."""
    match = re.search(r"\{.*\}", reply, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    teeth = set()
    for item in data.get("teeth", []):
        teeth.update(re.findall(r"\d+", str(item)))
    return sorted(teeth, key=int)


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=1)


def main():
    with open(NOTES_FILE) as f:
        notes = [line.strip() for line in f if line.strip()]
    with open(ANSWERS_FILE) as f:
        answers = [line.strip() for line in f if line.strip()]

    if len(notes) != len(answers):
        print(f"Files do not line up: {len(notes)} notes, {len(answers)} answers")
        return
    if sum(size for _, size in GROUPS) != len(notes):
        print(f"GROUPS add up to {sum(size for _, size in GROUPS)} "
              f"but there are {len(notes)} notes. Edit GROUPS at the top.")
        return

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    cache = load_cache()

    results = []  # one dict per note
    for number, (note, answer) in enumerate(zip(notes, answers), start=1):
        expected_field = answer.split("|")[0]
        expected = sorted(set(re.findall(r"\d+", expected_field)), key=int)

        if note not in cache:
            try:
                cache[note] = ask_llm(client, note)
                save_cache(cache)
            except Exception as error:  # e.g. no key, no credit, network
                print(f"Note {number}: API error: {error}")
                return
        llm_found = parse_teeth(cache[note])
        rules_found = find_teeth(note)

        results.append({
            "number": number, "note": note, "expected": expected,
            "rules": rules_found, "llm": llm_found,
            "rules_ok": rules_found == expected, "llm_ok": llm_found == expected,
        })

    # ----- Score by group -----
    print(f"\nModel: {MODEL}\n")
    print(f"{'group':42} {'notes':>5} {'rules':>7} {'LLM':>7}")
    start = 0
    for name, size in GROUPS:
        part = results[start:start + size]
        rules_score = sum(r["rules_ok"] for r in part)
        llm_score = sum(r["llm_ok"] for r in part)
        print(f"{name:42} {size:>5} {rules_score:>4}/{size:<2} {llm_score:>4}/{size:<2}")
        start += size
    total = len(results)
    print(f"{'ALL':42} {total:>5} "
          f"{sum(r['rules_ok'] for r in results):>4}/{total:<3}"
          f"{sum(r['llm_ok'] for r in results):>4}/{total:<3}")
    print("\nFair reading: I fixed my rules after seeing every group except the "
          "last one, so the rules' scores on the earlier groups are optimistic. "
          "The LLM was never tuned on any of them. The last group is the only "
          "one that is a fair head-to-head.")

    # ----- Show every note where either one is wrong -----
    print("\n----- Notes where rules or LLM is wrong -----")
    for r in results:
        if r["rules_ok"] and r["llm_ok"]:
            continue
        who = ("both wrong" if not r["rules_ok"] and not r["llm_ok"]
               else "rules wrong" if not r["rules_ok"] else "LLM wrong")
        print(f"\n#{r['number']} [{who}] {r['note']}")
        print(f"   expected: {r['expected']}")
        print(f"   rules:    {r['rules']}")
        print(f"   LLM:      {r['llm']}")


if __name__ == "__main__":
    main()