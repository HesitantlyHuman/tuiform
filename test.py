# Let's check how fast it is to clear rasterized
import time
import curses

screen = curses.initscr()
height, width = screen.getmaxyx()

needs_clear = [[False for _ in range(width)] for _ in range(height)]
x_bound = (0, 10)
y_bound = (5, 20)
for y in range(height):
    for x in range(width):
        if x > x_bound[0] and x < x_bound[1] and y > y_bound[0] and y < y_bound[1]:
            needs_clear[y][x] = True


def clear_new():
    for y in range(height):
        line = ""
        line_start = 0
        for x in range(width):
            if not needs_clear[y][x]:
                if len(line) > 0:
                    screen.addstr(y, line_start, line)
                line = ""
                line_start = x + 1
            else:
                line = " " + line
        if len(line) > 0:
            screen.addstr(y, line_start, line)


def clear_old():
    screen.clear()


iterations = 10_000

start_time = time.time()
for _ in range(iterations):
    clear_old()
    screen.addstr(0, 0, "Some random text")
end_time = time.time()
print(
    f"Old clear took {((end_time - start_time) / iterations) * 1000:0.2f}ms per iteration."
)

start_time = time.time()
for _ in range(iterations):
    clear_new()
    screen.addstr(0, 0, "Some random text")
end_time = time.time()
print(
    f"New clear took {((end_time - start_time) / iterations) * 1000:0.2f}ms per iteration."
)
