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
    text = re.sub(r"\b(permanent|adult)\s+", "", text)
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


def find_teeth_by_position(text):
    """Handle shorthand like 'lower right 6' -> 46, 'upper left 7' -> 27.
    Returns the FDI numbers found and the text with those phrases removed."""
    deciduous = "deciduous" in text
    table = DECIDUOUS_QUADRANT if deciduous else PERMANENT_QUADRANT
    teeth = []

    def add(jaw, side, position):
        teeth.append(f"{table[(jaw, side)]}{position}")
        return " "  # remove the phrase so the digit is not counted twice

    text = re.sub(r"\b(upper|lower)\s+(right|left)\s+([1-8])\b",
                  lambda m: add(m.group(1), m.group(2), m.group(3)), text)
    text = re.sub(r"\b(right|left)\s+(upper|lower)\s+([1-8])\b",
                  lambda m: add(m.group(2), m.group(1), m.group(3)), text)
    return teeth, text


def find_teeth_by_letter(text):
    """Baby teeth written with letters, e.g. 'upper right d' -> 54,
    'lower right e' -> 85. Letters: a=1 b=2 c=3 d=4 e=5 (central incisor to
    second molar). Only b-e are read, because a lone 'a' is usually just the
    English word 'a'. If no side is given ('lower d'), both sides are returned."""
    teeth = []
    letter_pos = {"b": 2, "c": 3, "d": 4, "e": 5}

    def add(jaw, side, letter):
        teeth.append(f"{DECIDUOUS_QUADRANT[(jaw, side)]}{letter_pos[letter]}")
        return " "

    text = re.sub(r"\b(upper|lower)\s+(right|left)\s+([b-e])\b",
                  lambda m: add(m.group(1), m.group(2), m.group(3)), text)
    text = re.sub(r"\b(right|left)\s+(upper|lower)\s+([b-e])\b",
                  lambda m: add(m.group(2), m.group(1), m.group(3)), text)

    def add_both_sides(m):
        add(m.group(1), "right", m.group(2))
        add(m.group(1), "left", m.group(2))
        return " "

    text = re.sub(r"\b(upper|lower)\s+([b-e])\b", add_both_sides, text)
    return teeth, text


def find_teeth(note):
    text = normalize(note)

    # 1) Remove numbers that are NOT tooth numbers:
    #    "class 2", "stage 3", "grade 3"
    text = re.sub(r"(class|stage|grade)\s*\d+", " ", text)
    #    ages: "8 year old", "45 years old", "6 yo"
    text = re.sub(r"\d+\s*(years?|yrs?|yo|y/o|months?|weeks?)\b(\s*old)?", " ", text)
    #    digits stuck to letters: "MB2", "mm2", "12mm"
    text = re.sub(r"\b[a-z]+\d+\b|\b\d+[a-z]+\b", " ", text)

    # 2) Shorthand like "lower right 6"
    teeth, text = find_teeth_by_position(text)

    # 2b) Baby teeth written as letters, like "upper right d"
    letter_teeth, text = find_teeth_by_letter(text)
    teeth += letter_teeth

    # 3) Normal tooth numbers
    teeth += re.findall(r"\d+", text)

    # 4) If there are no digits, look for tooth names instead
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