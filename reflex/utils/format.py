"""Formatting operations."""

from __future__ import annotations

import base64
import io
import json
import os
import os.path as op
import re
import sys
from typing import TYPE_CHECKING, Any, Type, Union

import plotly.graph_objects as go
from plotly.graph_objects import Figure
from plotly.io import to_json

from reflex import constants
from reflex.utils import types
from reflex.vars import Var

if TYPE_CHECKING:
    from reflex.components.component import ComponentStyle
    from reflex.event import EventChain, EventHandler, EventSpec

WRAP_MAP = {
    "{": "}",
    "(": ")",
    "[": "]",
    "<": ">",
    '"': '"',
    "'": "'",
    "`": "`",
}


def get_close_char(open: str, close: str | None = None) -> str:
    """Check if the given character is a valid brace.

    Args:
        open: The open character.
        close: The close character if provided.

    Returns:
        The close character.

    Raises:
        ValueError: If the open character is not a valid brace.
    """
    if close is not None:
        return close
    if open not in WRAP_MAP:
        raise ValueError(f"Invalid wrap open: {open}, must be one of {WRAP_MAP.keys()}")
    return WRAP_MAP[open]


def is_wrapped(text: str, open: str, close: str | None = None) -> bool:
    """Check if the given text is wrapped in the given open and close characters.

    Args:
        text: The text to check.
        open: The open character.
        close: The close character.

    Returns:
        Whether the text is wrapped.
    """
    close = get_close_char(open, close)
    return text.startswith(open) and text.endswith(close)


def wrap(
    text: str,
    open: str,
    close: str | None = None,
    check_first: bool = True,
    num: int = 1,
) -> str:
    """Wrap the given text in the given open and close characters.

    Args:
        text: The text to wrap.
        open: The open character.
        close: The close character.
        check_first: Whether to check if the text is already wrapped.
        num: The number of times to wrap the text.

    Returns:
        The wrapped text.
    """
    close = get_close_char(open, close)

    # If desired, check if the text is already wrapped in braces.
    if check_first and is_wrapped(text=text, open=open, close=close):
        return text

    # Wrap the text in braces.
    return f"{open * num}{text}{close * num}"


def indent(text: str, indent_level: int = 2) -> str:
    """Indent the given text by the given indent level.

    Args:
        text: The text to indent.
        indent_level: The indent level.

    Returns:
        The indented text.
    """
    lines = text.splitlines()
    if len(lines) < 2:
        return text
    return os.linesep.join(f"{' ' * indent_level}{line}" for line in lines) + os.linesep


def to_snake_case(text: str) -> str:
    """Convert a string to snake case.

    The words in the text are converted to lowercase and
    separated by underscores.

    Args:
        text: The string to convert.

    Returns:
        The snake case string.
    """
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", text)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def to_camel_case(text: str) -> str:
    """Convert a string to camel case.

    The first word in the text is converted to lowercase and
    the rest of the words are converted to title case, removing underscores.

    Args:
        text: The string to convert.

    Returns:
        The camel case string.
    """
    if "_" not in text:
        return text
    camel = "".join(
        word.capitalize() if i > 0 else word.lower()
        for i, word in enumerate(text.lstrip("_").split("_"))
    )
    prefix = "_" if text.startswith("_") else ""
    return prefix + camel


def to_title_case(text: str) -> str:
    """Convert a string from snake case to title case.

    Args:
        text: The string to convert.

    Returns:
        The title case string.
    """
    return "".join(word.capitalize() for word in text.split("_"))


def to_kebab_case(text: str) -> str:
    """Convert a string to kebab case.

    The words in the text are converted to lowercase and
    separated by hyphens.

    Args:
        text: The string to convert.

    Returns:
        The title case string.
    """
    return to_snake_case(text).replace("_", "-")


def format_string(string: str) -> str:
    """Format the given string as a JS string literal..

    Args:
        string: The string to format.

    Returns:
        The formatted string.
    """
    # Escape backticks.
    string = string.replace(r"\`", "`")
    string = string.replace("`", r"\`")

    # Wrap the string so it looks like {`string`}.
    string = wrap(string, "`")
    string = wrap(string, "{")

    return string


def format_var(var: Var) -> str:
    """Format the given Var as a javascript value.

    Args:
        var: The Var to format.

    Returns:
        The formatted Var.
    """
    if not var.is_local or var.is_string:
        return str(var)
    if types._issubclass(var.type_, str):
        return format_string(var.full_name)
    if is_wrapped(var.full_name, "{"):
        return var.full_name
    return json_dumps(var.full_name)


def format_route(route: str, format_case=True) -> str:
    """Format the given route.

    Args:
        route: The route to format.
        format_case: whether to format case to kebab case.

    Returns:
        The formatted route.
    """
    route = route.strip("/")
    # Strip the route and format casing.
    if format_case:
        route = to_kebab_case(route)

    # If the route is empty, return the index route.
    if route == "":
        return constants.INDEX_ROUTE

    return route


def format_cond(
    cond: str,
    true_value: str,
    false_value: str = '""',
    is_prop=False,
) -> str:
    """Format a conditional expression.

    Args:
        cond: The cond.
        true_value: The value to return if the cond is true.
        false_value: The value to return if the cond is false.
        is_prop: Whether the cond is a prop

    Returns:
        The formatted conditional expression.
    """
    # Import here to avoid circular imports.
    from reflex.vars import Var

    # Use Python truthiness.
    cond = f"isTrue({cond})"

    # Format prop conds.
    if is_prop:
        prop1 = Var.create_safe(true_value, is_string=type(true_value) is str).set(
            is_local=True
        )  # type: ignore
        prop2 = Var.create_safe(false_value, is_string=type(false_value) is str).set(
            is_local=True
        )  # type: ignore
        return f"{cond} ? {prop1} : {prop2}".replace("{", "").replace("}", "")

    # Format component conds.
    return wrap(f"{cond} ? {true_value} : {false_value}", "{")


def format_prop(
    prop: Union[Var, EventChain, ComponentStyle, str],
) -> Union[int, float, str]:
    """Format a prop.

    Args:
        prop: The prop to format.

    Returns:
        The formatted prop to display within a tag.

    Raises:
        TypeError: If the prop is not a valid type.
    """
    # import here to avoid circular import.
    from reflex.event import EVENT_ARG, EventChain

    try:
        # Handle var props.
        if isinstance(prop, Var):
            if not prop.is_local or prop.is_string:
                return str(prop)
            if types._issubclass(prop.type_, str):
                return format_string(prop.full_name)
            prop = prop.full_name

        # Handle event props.
        elif isinstance(prop, EventChain):
            chain = ",".join([format_event(event) for event in prop.events])
            event = f"Event([{chain}], {EVENT_ARG})"
            prop = f"{EVENT_ARG} => {event}"

        # Handle other types.
        elif isinstance(prop, str):
            if is_wrapped(prop, "{"):
                return prop
            return json_dumps(prop)

        elif isinstance(prop, Figure):
            prop = json.loads(to_json(prop))["data"]  # type: ignore

        # For dictionaries, convert any properties to strings.
        elif isinstance(prop, dict):
            prop = format_dict(prop)

        else:
            # Dump the prop as JSON.
            prop = json_dumps(prop)
    except TypeError as e:
        raise TypeError(f"Could not format prop: {prop} of type {type(prop)}") from e

    # Wrap the variable in braces.
    assert isinstance(prop, str), "The prop must be a string."
    return wrap(prop, "{", check_first=False)


def get_event_handler_parts(handler: EventHandler) -> tuple[str, str]:
    """Get the state and function name of an event handler.

    Args:
        handler: The event handler to get the parts of.

    Returns:
        The state and function name.
    """
    # Get the class that defines the event handler.
    parts = handler.fn.__qualname__.split(".")

    # If there's no enclosing class, just return the function name.
    if len(parts) == 1:
        return ("", parts[-1])

    # Get the state and the function name.
    state_name, name = parts[-2:]

    # Construct the full event handler name.
    try:
        # Try to get the state from the module.
        state = vars(sys.modules[handler.fn.__module__])[state_name]
    except Exception:
        # If the state isn't in the module, just return the function name.
        return ("", handler.fn.__qualname__)

    return (state.get_full_name(), name)


def format_event_handler(handler: EventHandler) -> str:
    """Format an event handler.

    Args:
        handler: The event handler to format.

    Returns:
        The formatted function.
    """
    state, name = get_event_handler_parts(handler)
    if state == "":
        return name
    return f"{state}.{name}"


def format_event(event_spec: EventSpec) -> str:
    """Format an event.

    Args:
        event_spec: The event to format.

    Returns:
        The compiled event.
    """
    args = ",".join(
        [
            ":".join(
                (name.name, json.dumps(val.name) if val.is_string else val.full_name)
            )
            for name, val in event_spec.args
        ]
    )
    event_args = [
        wrap(format_event_handler(event_spec.handler), '"'),
    ]
    event_args.append(wrap(args, "{"))

    if event_spec.client_handler_name:
        event_args.append(wrap(event_spec.client_handler_name, '"'))
    return f"E({', '.join(event_args)})"


def format_event_chain(
    event_chain: EventChain | Var[EventChain],
    event_arg: Var | None = None,
) -> str:
    """Format an event chain as a javascript invocation.

    Args:
        event_chain: The event chain to queue on the frontend.
        event_arg: The browser-native event (only used to preventDefault).

    Returns:
        Compiled javascript code to queue the given event chain on the frontend.

    Raises:
        ValueError: When the given event chain is not a valid event chain.
    """
    if isinstance(event_chain, Var):
        from reflex.event import EventChain

        if event_chain.type_ is not EventChain:
            raise ValueError(f"Invalid event chain: {event_chain}")
        return "".join(
            [
                "(() => {",
                format_var(event_chain),
                f"; preventDefault({format_var(event_arg)})" if event_arg else "",
                "})()",
            ]
        )

    chain = ",".join([format_event(event) for event in event_chain.events])
    return "".join(
        [
            f"Event([{chain}]",
            f", {format_var(event_arg)}" if event_arg else "",
            ")",
        ]
    )


def format_query_params(router_data: dict[str, Any]) -> dict[str, str]:
    """Convert back query params name to python-friendly case.

    Args:
        router_data: the router_data dict containing the query params

    Returns:
        The reformatted query params
    """
    params = router_data[constants.RouteVar.QUERY]
    return {k.replace("-", "_"): v for k, v in params.items()}


def format_dataframe_values(value: Type) -> list[Any]:
    """Format dataframe values.

    Args:
        value: The value to format.

    Returns:
        Format data
    """
    if not types.is_dataframe(type(value)):
        return value

    format_data = []
    for data in list(value.values.tolist()):
        element = []
        for d in data:
            element.append(str(d) if isinstance(d, (list, tuple)) else d)
        format_data.append(element)

    return format_data


def format_image_data(value: Type) -> str:
    """Format image data.

    Args:
        value: The value to format.

    Returns:
        Format data
    """
    buff = io.BytesIO()
    value.save(buff, format="PNG")
    image_bytes = buff.getvalue()
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"


def format_state(value: Any) -> Any:
    """Recursively format values in the given state.

    Args:
        value: The state to format.

    Returns:
        The formatted state.

    Raises:
        TypeError: If the given value is not a valid state.
    """
    # Handle dicts.
    if isinstance(value, dict):
        return {k: format_state(v) for k, v in value.items()}

    # Handle lists, sets, typles.
    if isinstance(value, types.StateIterBases):
        return [format_state(v) for v in value]

    # Return state vars as is.
    if isinstance(value, types.StateBases):
        return value

    # Convert plotly figures to JSON.
    if isinstance(value, go.Figure):
        return json.loads(to_json(value))["data"]  # type: ignore

    # Convert pandas dataframes to JSON.
    if types.is_dataframe(type(value)):
        return {
            "columns": value.columns.tolist(),
            "data": format_dataframe_values(value),
        }

    # Convert datetime objects to str.
    if types.is_datetime(type(value)):
        return str(value)

    # Convert Image objects to base64.
    if types.is_image(type(value)):
        return format_image_data(value)  # type: ignore

    raise TypeError(
        "State vars must be primitive Python types, "
        "or subclasses of rx.Base. "
        f"Got var of type {type(value)}."
    )


def format_ref(ref: str) -> str:
    """Format a ref.

    Args:
        ref: The ref to format.

    Returns:
        The formatted ref.
    """
    # Replace all non-word characters with underscores.
    clean_ref = re.sub(r"[^\w]+", "_", ref)
    return f"ref_{clean_ref}"


def format_array_ref(refs: str, idx: Var | None) -> str:
    """Format a ref accessed by array.

    Args:
        refs : The ref array to access.
        idx : The index of the ref in the array.

    Returns:
        The formatted ref.
    """
    clean_ref = re.sub(r"[^\w]+", "_", refs)
    if idx is not None:
        idx.is_local = True
        return f"refs_{clean_ref}[{idx}]"
    return f"refs_{clean_ref}"


def format_dict(prop: ComponentStyle) -> str:
    """Format a dict with vars potentially as values.

    Args:
        prop: The dict to format.

    Returns:
        The formatted dict.
    """
    # Import here to avoid circular imports.
    from reflex.vars import Var

    # Convert any var keys to strings.
    prop = {key: str(val) if isinstance(val, Var) else val for key, val in prop.items()}

    # Dump the dict to a string.
    fprop = json_dumps(prop)

    def unescape_double_quotes_in_var(m: re.Match) -> str:
        # Since the outer quotes are removed, the inner escaped quotes must be unescaped.
        return re.sub('\\\\"', '"', m.group(1))

    # This substitution is necessary to unwrap var values.
    fprop = re.sub(
        pattern=r"""
            (?<!\\)      # must NOT start with a backslash
            "            # match opening double quote of JSON value
            {(.*?)}      # extract the value between curly braces (non-greedy)
            "            # match must end with an unescaped double quote
        """,
        repl=unescape_double_quotes_in_var,
        string=fprop,
        flags=re.VERBOSE,
    )

    # Return the formatted dict.
    return fprop


def format_breadcrumbs(route: str) -> list[tuple[str, str]]:
    """Take a route and return a list of tuple for use in breadcrumb.

    Args:
        route: The route to transform.

    Returns:
        list[tuple[str, str]]: the list of tuples for the breadcrumb.
    """
    route_parts = route.lstrip("/").split("/")

    # create and return breadcrumbs
    return [
        (part, op.join("/", *route_parts[: i + 1]))
        for i, part in enumerate(route_parts)
    ]


def json_dumps(obj: Any) -> str:
    """Takes an object and returns a jsonified string.

    Args:
        obj: The object to be serialized.

    Returns:
        A string
    """
    return json.dumps(obj, ensure_ascii=False, default=list)
