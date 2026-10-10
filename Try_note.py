"""Type a messy dental note and see how it is turned into structured data.

Run:  python try_note.py
Type a note and press Enter. Press Enter on an empty line to quit.

Needs: pip install anthropic, and ANTHROPIC_API_KEY set in this terminal.
Use FICTIONAL notes only. Never type a real patient's name or details.
"""
import json
import re

import anthropic

from main import find_teeth  # my rule-based tooth finder

MODEL = "claude-sonnet-5-5"

SYSTEM_PROMPT = """You turn one short, messy dental clinic note into structured data.

Return JSON with these fields:
- "teeth": list of tooth numbers the note is about. If the note writes numbers as digits, return them exactly as written (do not convert between numbering systems). If the note names a tooth in words, shorthand (e.g. "UR6") or baby-tooth letters (e.g. "upper right d"), return the FDI number. Ignore numbers that are not teeth (ages, doses, measurements, classes, grades, shades). If the note names no tooth, return [].
- "system": "FDI", "Universal" or "unclear" - the numbering system the note seems to use. Many numbers (11-18, 21-28, 31, 32) are valid in both, so say "unclear" when you cannot tell.
- "diagnosis": the diagnosis or finding in a few words, or "not stated" if the note gives none.
- "procedure": the procedure done, in plain standard words (for example "root canal treatment", "extraction", "composite restoration"), several separated by "; ". Use "none" if nothing was done, even if something was only advised or planned.
- "uncertain": a short sentence about anything you had to guess, or "" if nothing.

Do not invent teeth, diagnoses or procedures that the note does not support. If you are unsure, say so in "uncertain".

Reply with only the JSON."""


def ask(client, note):
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": note}],
    )
    texts = [block.text for block in response.content
             if getattr(block, "type", "text") == "text"]
    return "\n".join(texts)


def parse(reply):
    match = re.search(r"\{.*\}", reply, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def main():
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    print("Type a fictional dental note (empty line to quit).")
    while True:
        note = input("\nNote: ").strip()
        if not note:
            break
        try:
            data = parse(ask(client, note))
        except Exception as error:
            print("API error:", error)
            continue
        if data is None:
            print("The AI's reply could not be read. Try again.")
            continue

        print("\n  AI result")
        print("  teeth:     ", data.get("teeth"))
        print("  system:    ", data.get("system"))
        print("  diagnosis: ", data.get("diagnosis"))
        print("  procedure: ", data.get("procedure"))
        if data.get("uncertain"):
            print("  unsure:    ", data["uncertain"])
        print("\n  My rules (tooth only):", find_teeth(note))
        print("  Check this yourself. The AI can be wrong, and diagnosis and "
              "procedure have not been scored against my answer key yet.")


if __name__ == "__main__":
    main()