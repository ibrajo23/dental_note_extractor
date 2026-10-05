import re

# ---------- Tooth names -> FDI numbers ----------
# Instead of typing every phrase, we describe a tooth by three things:
# jaw (upper/lower), side (right/left) and type (incisor, canine, molar...).
# The code then builds every matching FDI number.

# FDI quadrant digit for each (jaw, side)
PERMANENT_QUADRANT = {
    ("upper", "right"): 1, ("upper", "left"): 2,
    ("lower", "left"): 3, ("lower", "right"): 4,
}
DECIDUOUS_QUADRANT = {
    ("upper", "right"): 5, ("upper", "left"): 6,
    ("lower", "left"): 7, ("lower", "right"): 8,
}

# Tooth type -> position numbers. Longer phrases come first on purpose.
PERMANENT_TYPES = [
    ("central incisor", [1]),
    ("lateral incisor", [2]),
    ("incisor", [1, 2]),
    ("canine", [3]),
    ("cuspid", [3]),
    ("first premolar", [4]),
    ("second premolar", [5]),
    ("premolar", [4, 5]),
    ("first molar", [6]),
    ("second molar", [7]),
    ("third molar", [8]),
    ("wisdom", [8]),
    ("molar", [6, 7, 8]),
]
DECIDUOUS_TYPES = [
    ("central incisor", [1]),
    ("lateral incisor", [2]),
    ("incisor", [1, 2]),
    ("canine", [3]),
    ("cuspid", [3]),
    ("first molar", [4]),
    ("second molar", [5]),
    ("molar", [4, 5]),
]


def normalize(note):
    """Lowercase, fix spelling variants, turn 3rd -> third, remove plurals."""
    text = note.lower()
    text = re.sub(r"\bdecidou?s\b|\bdeciduous\b|\bprimary\b|\bbaby\b", "deciduous", text)
    text = re.sub(r"\b1st\b", "first", text)
    text = re.sub(r"\b2nd\b", "second", text)
    text = re.sub(r"\b3rd\b", "third", text)
    text = re.sub(r"\b(incisor|molar|premolar|canine|cuspid)s\b", r"\1", text)
    return text


def find_teeth_by_name(note):
    text = normalize(note)
    deciduous = "deciduous" in text

    # Side only counts when it sits next to the jaw word ("lower right"),
    # so words like "left untreated" are not mistaken for a side.
    pair = re.search(r"\b(upper|lower)\s+(right|left)\b", text)
    pair_rev = re.search(r"\b(right|left)\s+(upper|lower)\b", text)
    if pair:
        quadrants = [(pair.group(1), pair.group(2))]
    elif pair_rev:
        quadrants = [(pair_rev.group(2), pair_rev.group(1))]
    else:
        jaws = [j for j in ("upper", "lower") if re.search(rf"\b{j}\b", text)]
        if not jaws:
            jaws = ["upper", "lower"]
        quadrants = [(j, s) for j in jaws for s in ("right", "left")]

    types = DECIDUOUS_TYPES if deciduous else PERMANENT_TYPES
    positions = []
    for phrase, nums in types:
        if phrase in text:
            positions = nums
            break  # first (longest) match wins
    if not positions:
        return []

    table = DECIDUOUS_QUADRANT if deciduous else PERMANENT_QUADRANT
    return [f"{table[q]}{p}" for q in quadrants for p in positions]


def find_teeth(note):
    # 1) Remove "class 2", "stage 3", "grade 3" so they are not read as teeth
    text = normalize(note)
    cleaned = re.sub(r"(class|stage|grade)\s*\d+", "", text)
    teeth = re.findall(r"\d+", cleaned)

    # 2) If there are no digits, look for tooth names instead
    if not teeth:
        teeth = find_teeth_by_name(note)

    return sorted(set(teeth), key=int)


# ---------- Score against the answer key ----------
if __name__ == "__main__":
    with open("notes.txt") as f:
        notes = [line.strip() for line in f if line.strip()]

    with open("answers.txt") as f:
        answers = [line.strip() for line in f if line.strip()]

    print(len(notes), len(answers))

    correct = 0
    for note, answer in zip(notes, answers):
        found = find_teeth(note)
        expected_field = answer.split("|")[0]
        expected = sorted(set(re.findall(r"\d+", expected_field)), key=int)

        if found == expected:
            correct += 1
        else:
            print("WRONG:", found, "expected", expected, "<-", note)

    print(f"{correct}/{len(notes)} correct")
