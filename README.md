# tuiform
Event driven declarative terminal user interfaces, written in python.

## Plans
Will not support changing styles for now
Is async only

## Requires
python 3.10

## TODO
- How do we update based on user defined events?
    Maybe have elements register to watch for specific types of events. Have an event handler which will dispatch events to the appropriate elements.
- Better colors for the drawing (automatically convert into preset curses colors based on the session manager)
- Ensure that we require the session manager (maybe have the session manager return the window?)
- Virtual draw frames and scrolling
- Text input element

stretch
- Auto display of structured data