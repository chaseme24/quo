import inspect
import io
import itertools
import os
import struct
import sys
import math
import typing

from quo.accordance import (
        DEFAULT_COLUMNS,
        get_winterm_size,
        bit_bytes,
        isatty,
        strip_ansi_colors,
        )
from quo.color import ansi_color_codes, _ansi_reset_all
from quo.errors import Abort, UsageError
from quo.context.current import resolve_color_default
from quo.types import Choice, convert_type, ParamType
from quo.expediency import inscribe, LazyFile


# The prompt functions to use.  The doc tools currently override these
# functions to customize how they work.

insert: typing.Callable[[str], str] = input



def hidden_prompt_func(prompt: str) -> str:
    import getpass

    return getpass.getpass(prompt)

import enum

class EditingMode(enum.Enum):
    # The set of key bindings that is active.
    VI = "VI"
    EMACS = "EMACS"

#: Name of the search buffer.
SEARCH_BUFFER = "SEARCH_BUFFER"

#: Name of the default buffer.
DEFAULT_BUFFER = "DEFAULT_BUFFER"

#: Name of the system buffer.
SYSTEM_BUFFER = "SYSTEM_BUFFER"

def _build_prompt(
  text: str, 
  suffix: str, 
  show_default: bool = False, 
  default: typing.Optional[typing.Any] = None,
  show_choices: bool = True,
  type: typing.Optional[ParamType] = None
) -> str:
    prompt = text
    if type is not None and show_choices and isinstance(type, Choice):
        prompt += f" ({', '.join(map(str, type.choices))})"
    if default is not None and show_default:
        prompt = f"{prompt} [{_format_default(default)}]"
    return f"{prompt}{suffix}"


def _format_default(default: typing.Any) -> typing.Any:
    if isinstance(default, (io.IOBase, LazyFile)) and hasattr(default, "name"):
        return default.name

    return default

##################################################################


#############################


##########################################################################


def confirm(
        text: str, 
        default: typing.Optional[bool] = False, 
        abort: bool = False,
        suffix: str = ":>", 
        show_default: bool = True, 
        err: bool = False
        ) -> bool:
          
    """Prompts for confirmation (yes/no question).

    If the user aborts the input by sending a interrupt signal this
    function will catch it and raise a :exc:`Abort` exception.

    :param text: the question to ask.
    :param default: the default for the prompt.
    :param abort: if this is set to `True` a negative answer aborts the
                  exception by raising :exc:`Abort`.
    :param suffix: a suffix that should be added to the prompt.
    :param show_default: shows or hides the default value in the prompt.
    :param err: if set to true the file defaults to ``stderr`` instead of
                ``stdout``, the same as with echo.
    """
    prompt = _build_prompt(
        text, suffix, show_default, "Yes/no" if default else "yes/No"
    )
    while 1:
        try:
            echo(prompt, nl=False, err=err)
            value = insert("").lower().strip()
        except (KeyboardInterrupt, EOFError):
            raise Abort()
        if value in ("y", "yes"):
            rv = True
        elif value in ("n", "no"):
            rv = False
        elif default is not None and value == "":
            rv = default
        else:
            echo(f"ERROR:", bg="red", fg="black", nl=False)
            echo(f" ", nl=False)
            echo(f"invalid input", bg="yellow", fg="black", err=err)
            continue
        break
    if abort and not rv:
        raise Abort()
    return rv
##############################################
from quo.completion.auto_suggest import AutoSuggest
from .util import Completer
from quo.filters import FilterOrBool
from quo.keys.key_binding.key_bindings import KeyBindingsBase
from quo.text.core import Textual
from quo.history import History
from quo.lexers import Lexer
from quo.shortcuts.elicit import Elicit
from quo.styles import BaseStyle, StyleTransformation
from quo.i_o.output import ColorDepth
def promphgt(
    self,
    text: str = "",
    message: typing.Optional[Textual] = None,
    default: typing.Optional[typing.Any] = None,
    history: typing.Optional[History] = None,
    hide: bool = False,
    affirm: typing.Union[bool, str] = False,
    type: typing.Optional[typing.Union[ParamType, typing.Any]] = None,
    value_proc: typing.Optional[typing.Callable[[str], typing.Any]] = None,
    suffix: str = ":> ",
    show_default: bool = True,
    err: bool = False,
    show_choices: bool = True,
   ) -> typing.Any:
    from quo.shortcuts.elicit import Elicit
     

    """Prompts a user for input.  This is a convenience function that can be used to prompt a user for input later.

    If the user aborts the input by sending a interrupt signal, this  function will catch it and raise a :exc:`Abort` exception.

    :param text: the text to show for the prompt.
    :param default: the default value to use if no input happens.  If this  is not given it will prompt until it's aborted.
    :param hide: if this is set to true then the input value will  be hidden.
    :param affirm: asks for confirmation for the value.
    :param type: the type to use to check the value against.
    :param value_proc: if this parameter is provided it's a function that is invoked instead of the type conversion to convert a value.
    :param suffix: a suffix that should be added to the prompt.
    :param show_default: shows or hides the default value in the prompt.
    :param err: if set to true the file defaults to ``stderr`` instead of ``stdout``, the same as with echo.
    :param show_choices: Show or hide choices if the passed type is a Choice. For example if type is a Choice of either day or week, show_choices is true and text is "Group by" then the  prompt will be "Group by (day, week): ".

    """

    result = None

    def prompt_func(text: str) -> str:
      
        f = hidden_prompt_func if hide else insert
        try:
            inscribe(text, nl=False, err=err)
            return f("")
        except (KeyboardInterrupt, EOFError):
            # getpass doesn't print a newline if the user aborts input with ^C.
            # Allegedly this behavior is inherited from getpass(3).
            # A doc bug has been filed at https://bugs.python.org/issue24711
            if hide:
                inscribe(None, err=err)
            raise Abort("You've aborted input")

    if value_proc is None:
        value_proc = convert_type(type, default)

    prompt = _build_prompt(
        text, suffix, show_default, default, show_choices, type
    )

    while 1:
        while 1:
            value = prompt_func(prompt)
            if value:
                break
            elif default is not None:
                value = default
                break
        try:
            result = value_proc(value)
        except UsageError as e:
            if hide:
                inscribe("ERROR: the value you entered was invalid", err=err)
            else:
                inscribe(f"Error: {e.message}", err=err)  # noqa: B306
            continue
        if not affirm:
            return result
        while 1:
            value2 = prompt_func("Repeat for confirmation: ")
            if value2:
                break
        if value == value2:
            return result
        echo(f"ERROR:", nl=False, fg="black", bg="red")
        echo(f"The two entered values do not match", err=err, fg="black", bg="yellow")

###
def prompt(
    message: typing.Optional[Textual] = None,
    *,
    history: typing.Optional[History] = None,
    editing_mode: typing.Optional[EditingMode] = None,
    refresh_interval: typing.Optional[float] = None,
    suffix: str = ":> ",
    vi_mode: typing.Optional[bool] = None,
    lexer: typing.Optional[Lexer] = None,
    completer: typing.Optional[Completer] = None,
    complete_in_thread: typing.Optional[bool] = None,
    is_password: typing.Optional[bool] = None,
    key_bindings: typing.Optional[KeyBindingsBase] = None,
    bottom_toolbar: Optional[Textual] = None,
    style: typing.Optional[BaseStyle] = None,
    color_depth: typing.Optional[ColorDepth] = None,
    include_default_pygments_style: typing.Optional[FilterOrBool] = None,
    style_transformation: typing.Optional[StyleTransformation] = None,
    swap_light_and_dark_colors: typing.Optional[FilterOrBool] = None,
    rprompt: typing.Optional[Textual] = None,
    multiline: typing.Optional[FilterOrBool] = None,
    prompt_continuation: typing.Optional[PromptContinuationText] = None,
    wrap_lines: typing.Optional[FilterOrBool] = None,
    enable_history_search: typing.Optional[FilterOrBool] = None,
    search_ignore_case: typing.Optional[FilterOrBool] = None,
    complete_while_typing: typing.Optional[FilterOrBool] = None,
    validate_while_typing: typing.Optional[FilterOrBool] = None,
    complete_style: typing.Optional[CompleteStyle] = None,
    auto_suggest: typing.Optional[AutoSuggest] = None,
    validator: typing.Optional[Validator] = None,
    clipboard: typing.Optional[Clipboard] = None,
    mouse_support: typing.Optional[FilterOrBool] = None,
    input_processors: typing.Optional[List[Processor]] = None,
    placeholder: typing.Optional[Textual] = None,
    reserve_space_for_menu: typing.Optional[int] = None,
    enable_system_prompt: typing.Optional[FilterOrBool] = None,
    enable_suspend: typing.Optional[FilterOrBool] = None,
    enable_open_in_editor: typing.Optional[FilterOrBool] = None,
    tempfile_suffix: typing.Optional[typing.Union[str, typing.Callable[[], str]]] = None,
    tempfile: typing.Optional[typing.Union[str, typing.Callable[[], str]]] = None,
    # Following arguments are specific to the current `prompt()` call.
    default: str = "",
    accept_default: bool = False,
    pre_run: typing.Optional[typing.Callable[[], None]] = None,
) -> str:
    """
    The global `prompt` function. This will create a new `PromptSession`
    instance for every call.
    """
    # The history is the only attribute that has to be passed to the
    # `PromptSession`, it can't be passed into the `prompt()` method.
    session: Elicit[str] = Elicit(history=history)

    return session.prompt(
        message,
        editing_mode=editing_mode,
        refresh_interval=refresh_interval,
        vi_mode=vi_mode,
        lexer=lexer,
        completer=completer,
        complete_in_thread=complete_in_thread,
        is_password=is_password,
        key_bindings=key_bindings,
        bottom_toolbar=bottom_toolbar,
        style=style,
        color_depth=color_depth,
        include_default_pygments_style=include_default_pygments_style,
        style_transformation=style_transformation,
        swap_light_and_dark_colors=swap_light_and_dark_colors,
        rprompt=rprompt,
        multiline=multiline,
        prompt_continuation=prompt_continuation,
        wrap_lines=wrap_lines,
        enable_history_search=enable_history_search,
        search_ignore_case=search_ignore_case,
        complete_while_typing=complete_while_typing,
        validate_while_typing=validate_while_typing,
        complete_style=complete_style,
        auto_suggest=auto_suggest,
        validator=validator,
        clipboard=clipboard,
        mouse_support=mouse_support,
        input_processors=input_processors,
        placeholder=placeholder,
        reserve_space_for_menu=reserve_space_for_menu,
        enable_system_prompt=enable_system_prompt,
        enable_suspend=enable_suspend,
        enable_open_in_editor=enable_open_in_editor,
        tempfile_suffix=tempfile_suffix,
        tempfile=tempfile,
        default=default,
        accept_default=accept_default,
        pre_run=pre_run,
    )


prompt.__doc__ = Elicit.prompt.__doc__




def terminalsize()  -> os.terminal_size:
    """Returns the current size of the terminal as tuple in the form
    ``(width, height)`` in columns and rows.
    """
    import shutil

    if hasattr(shutil, "terminalsize"):
        return shutil.terminalsize()

    # We provide a sensible default for get_winterm_size() when being invoked
    # inside a subprocess. Without this, it would not provide a useful input.
    if get_winterm_size is not None:
        size = get_winterm_size()
        if size == (0, 0):
            return (79, 24)
        else:
            return size

    def ioctl_gwinsz(fd):
        try:
            import fcntl
            import termios

            cr = struct.unpack("hh", fcntl.ioctl(fd, termios.TIOCGWINSZ, "1234"))
        except Exception:
            return
        return cr

    cr = ioctl_gwinsz(0) or ioctl_gwinsz(1) or ioctl_gwinsz(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            try:
                cr = ioctl_gwinsz(fd)
            finally:
                os.close(fd)
        except Exception:
            pass
    if not cr or not cr[0] or not cr[1]:
        cr = (os.environ.get("LINES", 25), os.environ.get("COLUMNS", DEFAULT_COLUMNS))
    return int(cr[1]), int(cr[0])



def scrollable(text_or_generator, color=None):
    """This function takes a text and shows it via an environment specific
    pager on stdout.

    :param text_or_generator: the text to page, or alternatively, a
                              generator emitting the text to page.
    :param color: controls if the pager supports ANSI colors or not.  The
                  default is autodetection.
    """
    color = resolve_color_default(color)

    if inspect.isgeneratorfunction(text_or_generator):
        i = text_or_generator()
    elif isinstance(text_or_generator, str):
        i = [text_or_generator]
    else:
        i = iter(text_or_generator)

    # convert every element of i to a text type if necessary
    text_generator = (el if isinstance(el, str) else str(el) for el in i)

    from quo.implementation import pager

    return pager(itertools.chain(text_generator, "\n"), color)



def _interpret_color(color, offset=0):
    if isinstance(color, int):
        return f"{38 + offset};5;{color:d}"

    if isinstance(color, (tuple, list)):
        r, g, b = color
        return f"{38 + offset};2;{r:d};{g:d};{b:d}"

    return str(ansi_color_codes[color] + offset)


def flair(
    text: str,
    fg: typing.Optional[typing.Union[int, typing.Tuple[int, int, int], str]] = None,
    bg: typing.Optional[typing.Union[int, typing.Tuple[int, int, int], str]] = None,
    foreground: typing.Optional[typing.Union[int, typing.Tuple[int, int, int], str]] = None,
    background: typing.Optional[typing.Union[int, typing.Tuple[int, int, int], str]] = None,
    bold: typing.Optional[bool] = None,
    dim: typing.Optional[bool] = None,
    end=None,
    hidden=None,
    ul: typing.Optional[bool] = None,
    underline: typing.Optional[bool] = None,
    ov: typing.Optional[bool] = None,
    overline: typing.Optional[bool] = None,
    blink: typing.Optional[bool] = None,
    italic: typing.Optional[bool] = None,
    reverse=None,
    reset=True,
    strike: typing.Optional[bool] = None,
    ) -> str:
    """Styles a text with ANSI styles and returns the new string.  By
    default the styling is self contained which means that at the end
    of the string a reset code is issued.  This can be prevented by
    passing ``reset=False``.

    Examples::

        quo.inscribe(quo.style('Hello World!', foreground='green'))
        quo.echo(quo.style('ATTENTION!', blink=True))
        quo.echo(quo.style('Some things', reverse=True, foreground='cyan'))
        quo.echo(quo.style('More colors', foreground=(255, 12, 128), background=117))

  Note: v as in vblack or vred stands for vivid black or vivid red
  Supported color names:

    * ``black`` (might be a gray)
    * ``red``
    * ``green``
    * ``yellow`` (might be an orange)
    * ``blue``
    * ``magenta``
    * ``cyan``
    * ``white`` (might be light gray)
    * ``vblack``
    * ``vred``
    * ``vgreen``
    * ``vyellow``
    * ``vblue``
    * ``vmagenta``
    * ``vcyan``
    * ``vwhite``
    * ``reset`` (reset the color code only)

    If the terminal supports it, color may also be specified as:

    -   An integer in the interval [0, 255]. The terminal must support
        8-bit/256-color mode.
    -   An RGB tuple of three integers in [0, 255]. The terminal must
        support 24-bit/true-color mode.

    See https://en.wikipedia.org/wiki/ANSI_color and
    https://gist.github.com/XVilka/8346728 for more information.

    :param text: the string to style with ansi codes.
    :param foreground: if provided this will become the foreground color.
    :param background: if provided this will become the background color.
    :param bold: if provided this will enable or disable bold mode.
    :param dim: if provided this will enable or disable dim mode.  This is
                badly supported.
    :param underline: if provided this will enable or disable underline.
    :param blink: if provided this will enable or disable blinking.
    :param reverse: if provided this will enable or disable inverse
                    rendering (foreground becomes background and the
                    other way round).
    :param reset: by default a reset-all code is added at the end of the
                  string which means that styles do not carry over.  This
                  can be disabled to compose styles.

    """
    if not isinstance(text, str):
        text = str(text)

    bits = []


    if fg:
        try:
            bits.append(f"\033[{_interpret_color(fg)}m")
        except KeyError:
            raise TypeError(f"Unknown color {fg!r}")

    if foreground:
        try:
            bits.append(f"\033[{_interpret_color(foreground)}m")
        except KeyError:
            raise TypeError(f"Unknown color {foreground!r}")


    if bg:
        try:
            bits.append(f"\033[{_interpret_color(bg, 10)}m")
        except KeyError:
            raise TypeError(f"Unknown color {bg!r}")

    if background:
        try:
            bits.append(f"\033[{_interpret_color(background, 10)}m")
        except KeyError:
            raise TypeError(f"Unknown color {background!r}")

    if bold is not None:
        bits.append(f"\033[{1 if bold else 22}m")
    if dim is not None:
        bits.append(f"\033[{2 if dim else 22}m")
    if end is not None:
        pass
    if ov is not None:
        bits.append(f"\033[{53 if ov else 55}m") 
    if overline is not None:
        bits.append(f"\033[{53 if overline else 55}m")

    if ul is not None:
        bits.append(f"\033[{4 if ul else 24}m")
    if underline is not None:
        bits.append(f"\033[{4 if underline else 24}m")
    if blink is not None:
        bits.append(f"\033[{5 if blink else 25}m")
    if reverse is not None:
        bits.append(f"\033[{7 if reverse else 27}m") 
    if italic is not None:
        bits.append(f"\x1B[3m")
    if hidden is not None:
        bits.append(f"\x1b[8m")
    if strike is not None:
        bits.append(f"\x1b[9m")

    bits.append(text)
    if reset:
        bits.append(_ansi_reset_all)
    return "".join(bits)


def unstyle(text):
    """Removes ANSI styling information from a string.  Usually it's not
    necessary to use this function as quo's echo function will
    automatically remove styling if necessary.

    :param text: the text to remove style information from.
    """
    return strip_ansi_colors(text)


def edit(
        text=None, 
        editor=None, 
        env=None, 
        require_save=True, 
        extension=".txt", 
        filename=None
):
    r"""Edits the given text in the defined editor.  If an editor is given
    (should be the full path to the executable but the regular operating
    system search path is used for finding the executable) it overrides
    the detected editor.  Optionally, some environment variables can be
    used.  If the editor is closed without changes, `None` is returned.  In
    case a file is edited directly the return value is always `None` and
    `require_save` and `extension` are ignored.

    If the editor cannot be opened a :exc:`UsageError` is raised.

    Note for Windows: to simplify cross-platform usage, the newlines are
    automatically converted from POSIX to Windows and vice versa.  As such,
    the message here will have ``\n`` as newline markers.

    :param text: the text to edit.
    :param editor: optionally the editor to use.  Defaults to automatic
                   detection.
    :param env: environment variables to forward to the editor.
    :param require_save: if this is true, then not saving in the editor
                         will make the return value become `None`.
    :param extension: the extension to tell the editor about.  This defaults
                      to `.txt` but changing this might change syntax
                      highlighting.
    :param filename: if provided it will edit this file instead of the
                     provided text contents.  It will not use a temporary
                     file as an indirection in that case.
    """
    from quo.implementation import Editor

    editor = Editor(
        editor=editor, env=env, require_save=require_save, extension=extension
    )
    if filename is None:
        return editor.edit(text)
    editor.edit_file(filename)


def launch(url, wait=False, locate=False):
    """This function launches the given URL (or filename) in the default
    viewer application for this file type.  If this is an executable, it
    might launch the executable in a new session.  The return value is
    the exit code of the launched application.  Usually, ``0`` indicates
    success.

    Examples::

        quo.launch('https://quo.readthedocs.org/')
        quo.launch('/my/downloaded/file', locate=True)

    :param url: URL or filename of the thing to launch.
    :param wait: Wait for the program to exit before returning. This
        only works if the launched program blocks. In particular,
        ``xdg-open`` on Linux does not block.
    :param locate: if this is set to `True` then instead of launching the
                   application associated with the URL it will attempt to
                   launch a file manager with the file located.  This
                   might have weird effects if the URL does not point to
                   the filesystem.
    """
    from quo.implementation import open_url

    return open_url(url, wait=wait, locate=locate)

def raw_terminal():
    from quo.implementation import raw_terminal as f
    return f()


def echo(
        message=None,
        file: typing.Optional[typing.IO[str]] = None,
        nl=True,
        err=False,
        color=None,
        **styles
        ):
    """
    quo.echo('Hello World!', fg='green')
        quo.inscribe(quo.style('Hello World!', fg='green'))
    All keyword arguments are forwarded to the underlying functions
    depending on which one they go with.
    Non-string types will be converted to :class:`str`. However,
    :class:`bytes` are passed directly to :meth:`inscribe` without applying
    style. If you want to style bytes that represent text, call
    :meth:`bytes.decode` first.
    """

    if message is not None and not bit_bytes(message):
        message = flair(message, **styles)

    return inscribe(message, file=file, nl=nl, err=err, color=color)
