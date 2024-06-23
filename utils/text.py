"""Wrap.py

Break paragraphs into lines, attempting to avoid short lines.

We use the dynamic programming idea of Knuth-Plass to find the
optimal set of breaks according to a penalty function that
penalizes short lines quadratically; this can be done in linear
time via the OnlineConcaveMinima algorithm in SMAWK.py.

D. Eppstein, August 2005. (modified)
"""

from typing import Callable, List

from autograder.logging.tui.utils.smawk import OnlineConcaveMinima


# TODO: Update this to allow for breaking words if necessary (with a large penalty, of course)
# TODO: Maybe do this by creating a secondary function which automatically adds soft hyphens
def smart_wrap_text(
    text: str,
    target_width: int = 76,  # maximum length of a wrapped line
    allow_short_final_line: bool = True,  # True if last line should be as long as others
    french_spacing: bool = True,  # Single space instead of double after periods
    length_measure_function: Callable[
        [str], int
    ] = len,  # how to measure the length of a word
    line_too_long_penalty: int = 1250,  # penalize long lines by overpen*(len-target)
    too_many_lines_penalty: int = 1000,  # penalize more lines than optimal
    widow_penalty: int = 25,  # penalize really short last line
    hyphen_breaking_penalty: int = 25,
) -> List[str]:  # penalize breaking hyphenated words
    """Wrap the given text, returning a sequence of lines and minimizing raggedness.

    Wraps the the text using the SMAWK solving algorithm to solve the Knuth-Plass text
    raggedness algorithm in linear time. Will attempt to maintain as close to target
    width as possible for all lines, without going over. By default french spacing is
    used (one space after sentences, etc.). `widow_penalty` will penalize a last line
    which only has a single word.
    """

    # Make sequence of tuples (word, spacing if no break, cum.measure).
    words = []
    total = 0
    spacings = [0, length_measure_function(" "), length_measure_function("  ")]
    for hyphenword in text.split():
        if words:
            total += spacings[words[-1][1]]
        parts = hyphenword.split("-")
        for word in parts[:-1]:
            word += "-"
            total += length_measure_function(word)
            words.append((word, 0, total))
        word = parts[-1]
        total += length_measure_function(word)
        spacing = 1
        if word.endswith(".") and (len(hyphenword) > 2 or not hyphenword[0].isupper()):
            spacing = 2 - french_spacing
        words.append((word, spacing, total))

    # Define penalty function for breaking on line words[i:j]
    # Below this definition we will set up cost[i] to be the
    # total penalty of all lines up to a break prior to word i.
    def penalty(i, j):
        if j > len(words):
            return -i  # concave flag for out of bounds
        total = cost.value(i) + too_many_lines_penalty
        prevmeasure = i and (words[i - 1][2] + spacings[words[i - 1][1]])
        linemeasure = words[j - 1][2] - prevmeasure
        if linemeasure > target_width:
            total += line_too_long_penalty * (linemeasure - target_width)
        elif j < len(words) or not allow_short_final_line:
            total += (target_width - linemeasure) ** 2
        elif i == j - 1:
            total += widow_penalty
        if not words[j - 1][1]:
            total += hyphen_breaking_penalty
        return total

    # Apply concave minima algorithm and backtrack to form lines
    cost = OnlineConcaveMinima(penalty, 0)
    pos = len(words)
    lines = []
    while pos:
        breakpoint = cost.index(pos)
        line = []
        for i in range(breakpoint, pos):
            line.append(words[i][0])
            if i < pos - 1 and words[i][1]:
                line.append(" " * words[i][1])
        lines.append("".join(line))
        pos = breakpoint
    lines.reverse()
    return lines


def cut_line_with_ellipse(line: str, width: int) -> str:
    cut_line = line[:width]
    for idx_from_end in range(len(cut_line) - 2, -1, -1):
        if not line[idx_from_end].isspace():
            break
    idx_from_end = min(idx_from_end + 1, len(cut_line) - 1)
    cut_line = cut_line[:idx_from_end] + "…"
    return cut_line


def right_pad_line(line: str, width: int, padding_character: str = " ") -> str:
    if len(line) < width:
        line = line + padding_character * (width - len(line))
    return line


if __name__ == "__main__":
    print(cut_line_with_ellipse("Here is a line which should be cut.", 12))
