import curses

def main(win):
    win.nodelay(True)  # make getkey() not wait
    x = 0
    while True:
        # just to show that the loop runs, print a counter
        win.clear()
        win.addstr(0, 0, str(x))
        x += 1

        try:
            key = win.getkey()
        except:  # in no delay mode getkey raise and exeption if no key is press
            key = None
        if key == " ":  # of we got a space then break
            break


# a wrapper to create a window, and clean up at the end
curses.wrapper(main)