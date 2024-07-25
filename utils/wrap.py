"""wrap.py

Break paragraphs into lines, attempting to avoid short lines.
Inserts soft hyphens to break large words, if necessary.

We use the dynamic programming idea of Knuth-Plass to find the
optimal set of breaks according to a penalty function that
penalizes short lines quadratically; this can be done in linear
time via the OnlineConcaveMinima algorithm in SMAWK.py.

D. Eppstein, August 2005. (modified by Tanner Sims Jul 2024)
"""

import pyphen
from typing import Callable, List

from autograder.logging.tui.utils.smawk import OnlineConcaveMinima


dic = pyphen.Pyphen(lang="en")


def soft_hyphenate_text(text: str) -> str:
    output = []
    lines = text.split("\n")
    for line in lines:
        line_out = []
        words = line.split(" ")
        for word in words:
            line_out.append(dic.inserted(word, "\u00AD"))
        output.append(" ".join(line_out))
    output = "\n".join(output)
    output = output.replace("-\u00AD", "-")
    return output


def smart_wrap_text(
    text: str,
    target_width: int = 76,  # maximum length of a wrapped line
    allow_short_final_line: bool = True,  # True if last line should be as long as others
    length_measure_function: Callable[
        [str], int
    ] = len,  # how to measure the length of a word
    maximum_word_chunk_size: int = None,
    line_too_long_penalty: int = 1250,  # penalize long lines by overpen*(len-target)
    too_many_lines_penalty: int = 1000,  # penalize more lines than optimal
    widow_penalty: int = 30,  # penalize really short last line
    hyphen_breaking_penalty: int = 20,
    soft_hyphen_breaking_penalty: int = 40,
    non_hyphen_breaking_penalty: int = 100,
) -> List[str]:  # penalize breaking hyphenated words
    """Wrap the given text, returning a sequence of lines and minimizing raggedness.

    Wraps the the text using the SMAWK solving algorithm to solve the Knuth-Plass text
    raggedness algorithm in linear time. Will attempt to maintain as close to target
    width as possible for all lines, without going over. By default french spacing is
    used (one space after sentences, etc.). `widow_penalty` will penalize a last line
    which only has a single word.
    """

    # TODO: add some type checking

    if maximum_word_chunk_size is None:
        maximum_word_chunk_size = target_width // 5

    text = soft_hyphenate_text(text)

    # Make sequence of tuples (word, spacing if no break, spacing if break, is word break, cum.measure).
    words = []
    sizes = {
        "none": 0,
        "space": length_measure_function(" "),
        "hyphen": length_measure_function("-"),
    }
    characters = {"none": "", "space": " ", "hyphen": "-"}

    text = " ".join(text.split()).strip()  # TODO: Avoid if possible

    cumulative_length = 0
    current_word_start_index = 0
    for current_index in range(len(text)):
        character = text[current_index]
        word_length = length_measure_function(
            text[current_word_start_index:current_index]
        )
        if len(words) > 0 and (
            character in [" ", "-", "\u00AD"] or word_length >= maximum_word_chunk_size
        ):
            cumulative_length += sizes[words[-1][1]]

        if character == " ":
            word = text[current_word_start_index:current_index]
            cumulative_length += length_measure_function(word)
            words.append((word, "space", "none", False, cumulative_length))
            current_word_start_index = current_index + 1
        elif character == "-":
            word = text[current_word_start_index : current_index + 1]
            cumulative_length += length_measure_function(word)
            words.append((word, "none", "none", False, cumulative_length))
            current_word_start_index = current_index + 1
        elif character == "\u00AD":
            word = text[current_word_start_index:current_index]
            cumulative_length += length_measure_function(word)
            words.append((word, "none", "hyphen", False, cumulative_length))
            current_word_start_index = current_index + 1
        elif word_length >= maximum_word_chunk_size:
            word = text[current_word_start_index : current_index + 1]
            cumulative_length += length_measure_function(word)
            words.append((word, "none", "hyphen", True, cumulative_length))
            current_word_start_index = current_index + 1
    word = text[current_word_start_index : len(text)]
    cumulative_length += length_measure_function(word)
    words.append((word, "space", "none", False, cumulative_length))

    # Define penalty function for breaking on line words[i:j]
    # Below this definition we will set up cost[i] to be the
    # total penalty of all lines up to a break prior to word i.
    def penalty(i, j):
        if j > len(words):
            return -i  # concave flag for out of bounds
        penalty = cost.value(i) + too_many_lines_penalty
        prevmeasure = i and (words[i - 1][4] + sizes[words[i - 1][1]])
        linemeasure = words[j - 1][4] - prevmeasure + sizes[words[j - 1][2]]

        if linemeasure > target_width:
            penalty += line_too_long_penalty * (linemeasure - target_width)
        elif j < len(words) or not allow_short_final_line:
            penalty += (target_width - linemeasure) ** 2
        elif i == j - 1:
            penalty += widow_penalty

        if words[j - 1][1] == "none" and words[j - 1][2] == "none":
            penalty += hyphen_breaking_penalty
        elif words[j - 1][2] == "hyphen":
            if words[j - 1][3]:
                penalty += non_hyphen_breaking_penalty
            else:
                penalty += soft_hyphen_breaking_penalty
        return penalty

    # Apply concave minima algorithm and backtrack to form lines
    cost = OnlineConcaveMinima(penalty, 0)
    pos = len(words)
    lines = []
    while pos:
        breakpoint = cost.index(pos)
        line = []
        for i in range(breakpoint, pos):
            line.append(words[i][0])
            if i < pos - 1:
                line.append(characters[words[i][1]])
        line.append(characters[words[i][2]])
        lines.append("".join(line))
        pos = breakpoint
    lines.reverse()
    return lines


def cut_line_with_ellipse(line: str, width: int) -> str:
    if width == 0:
        return ""
    elif width == 1:
        return "…"
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
    # print(cut_line_with_ellipse("Here is a line which should be cut.", 12))
    # print(
    #     smart_wrap_text(
    #         "Many dictionaries are included in pyphen, they come from the Libre\u00ADOffice-git-repository and are distributed under GPL, LGPL and/or MPL. Dictionaries are not modified in this repository. See the dictionaries and LibreOffice's repository for more details."
    #     )
    # )
    # print(smart_wrap_text("Areallylongwordthatisjustallmashedtogether", 20))
    print(
        "\n".join(
            smart_wrap_text(
                "Here is some text¶ that we would like to have wrap very nicely and not exceed our cute little text box area. And the text, just does not stop. Just goes on and on and on, and there might even be some tremendously exceptionally long words occassionally",
                80,
            )
        )
    )
