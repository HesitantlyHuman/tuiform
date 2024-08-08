from typing import List, Sequence


# TODO: Do we want to allow a minimum and maximum?
def split_int(size: int, splits: int | List[int | float | None]) -> List[int]:
    """
    Splits the provided `size` int into integer subchunks based on the provided
    splits.

    If `splits` is an int, then `size` will be split into that many equal
    chunks.

    If `splits` is a list, then `size` will be split int `len(splits)` number
    of chunks, where the size of each chunk is controled by the corresponding
    element of the `splits` list. In this case, `size` will be split by
    allocating the splits on a first-come first-serve basis. Each element will
    be assessed one by one, and will take from the available total in `size`,
    before evaluating the next element in the list. The behaviors for each
    element are as follows:
        - If the element is an int, then that split will take either the
        specified amount, or the remaining total, whichever is smaller.
        - If the element is a float, it is expected that the element is
        between 0 and 1. That split will take either a rounded proportion of
        the total size (`round(proportion * size)`), or the remaining total,
        whichever is smaller.
        - If the element is None, then it will be skipped. After all other
        allocations have been calculated, the remaining total from `size` will
        be split evenly among each of the `None` elements.

    If at any point, it is not possible to split evenly (Either `splits` is an
    `int`, or we have multiple `None` splits), then the remainder will be
    allocated by adding one to the first N chunks, where N is the remainder.

    It is possible to not have enough splits to consume all of `size` (or no
    `None` splits to take the excess), in which case the output will have a sum
    which is less than `size`. Additionally, it is possible to have too many
    splits. In this case, the first come first serve strategy will leave all of
    the final chunks with a size of 0.
    """
    if isinstance(splits, int):
        base = size // splits
        remainder = size % splits
        return [base + int(idx < remainder) for idx in range(splits)]
    elif isinstance(splits, Sequence):
        # Allocate all of the non-None splits
        split_lengths = []
        nones = []
        remaining_length = size
        for i, split in enumerate(splits):
            if remaining_length <= 0:
                split_lengths.append(0)
            elif split is None:
                nones.append(i)
                split_lengths.append(None)
            elif isinstance(split, float):
                if split < 0 or split > 1:
                    raise ValueError("")  # TODO: write error
                used_length = min(round(size * split), remaining_length)
                split_lengths.append(used_length)
                remaining_length -= used_length
            elif isinstance(split, int):
                used_length = min(split, remaining_length)
                split_lengths.append(used_length)
                remaining_length -= used_length

        if remaining_length <= 0 or len(nones) == 0:
            return split_lengths

        # Now we will split the remaining length among the Nones
        none_lengths = split_int(remaining_length, len(nones))
        for none_index, none_length in zip(nones, none_lengths):
            split_lengths[none_index] = none_length

        return split_lengths
    else:
        raise ValueError(
            f"`split_size` expected `splits` type of int or sequence, received type of {type(splits)} instead."
        )


if __name__ == "__main__":
    print(split_int(20, 7))
    print(split_int(20, [5, None, None]))
    print(split_int(50, [1, 10, 50, 3]))
    print(split_int(50, [1, 10]))
