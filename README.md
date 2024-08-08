# tuiform
Event driven declarative terminal user interfaces, written in python.

## Plans
Will not support changing styles for now
Is async only


What if we integrated the draw calls for the components into the code
Then with a session manager context thing, we would collect all of those components and display and update them automatically?

## How can we get the framing to be seamless?
- Parent queries size of child, via constraints (Every component needs this)
- Then parent sets the child frame (how can we automate this?, maybe just have a sub function on the child, which then references the parent?)
    - This causes the child framing call to run

## Requires
python 3.10

## TODO
- Cache draw calls from components which have not been updated. We will still run the calls, but avoid any of the logic needed to generate them
- How do we update based on user defined events?
    Maybe have elements register to watch for specific types of events. Have an event handler which will dispatch events to the appropriate elements.
- Better colors for the drawing (automatically convert into preset curses colors based on the session manager)
- Ensure that we require the session manager (maybe have the session manager return the window?)
- Virtual draw frames and scrolling
- Text input element
- Table element
- List element
- Checkbox
- Fix the colors for vs code (maybe detecting the terminal somehow?)
- Rename TUIWindow to TUIForm, and TUIElement to TUIComponent
- Redirect stdout to an output file or stored buffer
- Progress bar
- Liveness indicator
- Graph
- Maybe rename DrawFrame to ScreenRegion or something?
- Do we want to be able to have multiple windows? Do we want to allow the user to resize panels and what not?

stretch
- Auto display of structured data