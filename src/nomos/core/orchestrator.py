"""Session orchestrator (actor) — skeleton.

Implements the minimal API used by the examples:
- create_session() -> returns an object with .id
- stream(session_id, inputs=None) -> async iterator of SessionEvent objects
- input(session_id, inputs) -> enqueue user messages
- control(session_id, command) -> apply control (pause/resume/cancel/checkpoint)
- materialize_state(session_id) -> SessionState (dict)

Verbose mode (verbose=True) provides detailed logging of:
- Session lifecycle events
- Messages sent to LLM providers
- Decisions received from providers
- Node transitions and routing
- Tool execution details

This is a simplified first pass to enable incremental development; real decision/tool execution
will be added as LLMProvider/ToolRunner adapters become available.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .events import EventType, SessionEvent, TokenFrame, DecisionFrame
from nomos.graph import AgentSpec
from .state import SessionState
from .store.memory import InMemoryEventStore
from .store.checkpoint_memory import InMemoryCheckpointStore
from .interfaces import LLMProvider, ToolRunner
from .observe import inc, span, measure
from .redaction import redact_mapping
from .schemas import SessionInput, ControlCommand


# Initialize rich console for verbose logging
_console = Console()


@dataclass
class _Session:
    id: str


def _format_messages_table(messages: List[Dict[str, Any]]) -> Table:
    """Format messages as a rich table."""
    table = Table(
        title="Messages Sent to LLM", show_header=True, header_style="bold magenta"
    )
    table.add_column("Role", style="cyan")
    table.add_column("Content Preview", style="white")

    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # Handle content parts
        if isinstance(content, list):
            content_text = " ".join(
                [part.get("data", "") for part in content if isinstance(part, dict)]
            )
        else:
            content_text = str(content)

        preview = content_text
        table.add_row(role, preview)

    return table


def _format_decision(decision_data: Dict[str, Any]) -> Panel:
    """Format decision as a rich panel."""
    action = decision_data.get("action", "UNKNOWN")
    color_map = {
        "MOVE": "blue",
        "TOOL_CALL": "yellow",
        "RESPOND": "green",
        "END": "red",
    }
    color = color_map.get(action, "white")

    content = Text()
    content.append("Action: ", style="bold")
    content.append(f"{action}\n", style=f"bold {color}")

    if action == "MOVE":
        step_id = decision_data.get("step_id")
        content.append("Target Step: ", style="bold")
        content.append(f"{step_id}", style="cyan")
    elif action == "TOOL_CALL":
        tool_call = decision_data.get("tool_call", {})
        tool_name = tool_call.get("tool_name")
        tool_kwargs = tool_call.get("tool_kwargs", {})
        content.append("Tool: ", style="bold")
        content.append(f"{tool_name}\n", style="cyan")
        content.append(f"Args: {tool_kwargs}", style="dim")
    elif action == "RESPOND":
        response = decision_data.get("response", "")
        content.append("Response: ", style="bold")
        content.append(f"{response}", style="green")

    return Panel(content, title="🤖 Decision", border_style=color, expand=False)


def _format_routing(from_node: str, to_node: str, condition: str = "") -> Panel:
    """Format routing transition as a rich panel."""
    content = Text()
    content.append(f"{from_node}", style="cyan")
    content.append(" → ", style="bold yellow")
    content.append(f"{to_node}", style="green")
    if condition:
        content.append(f"\nCondition: {condition}", style="dim")

    return Panel(content, title="🔀 Routing", border_style="yellow")


def _format_tool_execution(tool_name: str, tool_kwargs: Dict[str, Any]) -> Panel:
    """Format tool execution as a rich panel."""
    content = Text()
    content.append("Tool: ", style="bold")
    content.append(f"{tool_name}\n", style="cyan")
    content.append(f"Args: {tool_kwargs}", style="dim")

    return Panel(content, title="🔧 Tool Call", border_style="yellow", expand=False)


class Orchestrator:
    def __init__(
        self,
        agent: Any,  # noqa: ANN401
        *,
        store: Optional[InMemoryEventStore] = None,
        provider: Optional[LLMProvider] = None,
        tool_runner: Optional[ToolRunner] = None,
        checkpoint_store: Optional[InMemoryCheckpointStore] = None,
        redact: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        node_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
        verbose: bool = False,
    ) -> None:
        self._agent = agent
        self._store = store or InMemoryEventStore()
        self._provider = provider
        self._tool_runner = tool_runner
        self._checkpoint_store = checkpoint_store or InMemoryCheckpointStore()
        self._input_queues: Dict[str, asyncio.Queue[Dict[str, Any]]] = {}
        self._workers: Dict[str, asyncio.Task] = {}
        self._current_node: Dict[str, Optional[str]] = {}
        self._messages: Dict[str, List[Dict[str, Any]]] = {}
        self._cancel_flags: Dict[str, bool] = {}
        self._cancel_events: Dict[str, asyncio.Event] = {}
        self._resume_events: Dict[str, asyncio.Event] = {}
        self._redact = redact
        self._node_overrides: Dict[str, Dict[str, Any]] = node_overrides or {}
        self._verbose = verbose
        self._logger = logging.getLogger(__name__)

    async def _append(self, session_id: str, events: list[SessionEvent]) -> None:
        if self._redact:
            safe = []
            for ev in events:
                redacted_data = self._redact(ev.data)
                safe.append(
                    SessionEvent(
                        session_id=ev.session_id,
                        type=ev.type,
                        data=redacted_data,
                        node_id=ev.node_id,
                        event_id=ev.event_id,
                    )
                )
        else:
            # always minimally redact known sensitive keys in event data (best-effort)
            safe = []
            for ev in events:
                redacted_data = redact_mapping(ev.data)
                safe.append(
                    SessionEvent(
                        session_id=ev.session_id,
                        type=ev.type,
                        data=redacted_data,
                        node_id=ev.node_id,
                        event_id=ev.event_id,
                    )
                )
        await self._store.append(session_id, safe)

    async def create_session(self) -> _Session:
        sid = str(uuid.uuid4())

        if self._verbose:
            _console.rule("[bold cyan]Session Created[/bold cyan]")
            _console.print(f"Session ID: [bold green]{sid}[/bold green]")

        self._input_queues[sid] = asyncio.Queue()
        self._cancel_flags[sid] = False
        self._cancel_events[sid] = asyncio.Event()
        self._resume_events[sid] = asyncio.Event()
        self._resume_events[sid].set()
        # initialize current node from AgentSpec if available
        if isinstance(self._agent, AgentSpec):
            self._current_node[sid] = self._agent.start

            if self._verbose:
                _console.print(
                    f"Starting node: [bold blue]{self._agent.start}[/bold blue]"
                )
        else:
            self._current_node[sid] = None
        await self._append(
            sid,
            [
                SessionEvent(session_id=sid, type=EventType.SESSION_CREATED, data={}),
            ],
        )
        inc(EventType.SESSION_CREATED.value)
        return _Session(id=sid)

    async def input(
        self, session_id: str, inputs: Union[SessionInput, Dict[str, Any]]
    ) -> None:
        if isinstance(inputs, dict):
            inputs = SessionInput.model_validate(inputs)
        assert isinstance(inputs, SessionInput)
        # Accumulate messages
        self._messages.setdefault(session_id, []).extend(
            [
                msg.model_dump() if hasattr(msg, "model_dump") else msg
                for msg in inputs.messages
            ]
        )
        await self._append(
            session_id,
            [
                SessionEvent(
                    session_id=session_id,
                    type=EventType.INPUT_ENQUEUED,
                    data=inputs.model_dump(),
                ),
            ],
        )
        inc(EventType.INPUT_ENQUEUED.value)
        await self._input_queues[session_id].put(inputs.model_dump())
        # Ensure a worker is running to process this input
        if session_id not in self._workers:
            self._workers[session_id] = asyncio.create_task(self._worker(session_id))

    async def _worker(self, session_id: str) -> None:
        """Process queued inputs for a session using the provider (if available)."""
        q = self._input_queues[session_id]
        while True:
            payload = await q.get()

            try:
                # Honor pause
                await self._resume_events[session_id].wait()
                # Start decision
                current_node_id = self._current_node.get(session_id)

                if self._verbose:
                    _console.rule(f"[bold yellow]Node: {current_node_id}[/bold yellow]")

                await self._append(
                    session_id,
                    [
                        SessionEvent(
                            session_id=session_id,
                            type=EventType.DECISION_STARTED,
                            data={},
                            node_id=self._current_node.get(session_id),
                        ),
                    ],
                )
                inc(EventType.DECISION_STARTED.value)
                if not self._provider:
                    # No provider wired: emit a trivial completion
                    await self._append(
                        session_id,
                        [
                            SessionEvent(
                                session_id=session_id,
                                type=EventType.DECISION_COMPLETED,
                                data={
                                    "action": "RESPOND",
                                    "response": "(provider not configured)",
                                },
                            )
                        ],
                    )
                    inc(EventType.DECISION_COMPLETED.value)
                    continue

                # Resolve node-level overrides
                current_node_id = self._current_node.get(session_id)
                ov = self._node_overrides.get(current_node_id or "", {})
                eff_provider = ov.get("provider", self._provider) or self._provider
                eff_tool_runner = (
                    ov.get("tool_runner", self._tool_runner) or self._tool_runner
                )

                # Agent loop: continue making decisions within this input until RESPOND or max turns
                turns = 0
                messages_base = list(self._messages.get(session_id, []))
                while True:
                    turns += 1
                    if turns > 5:  # Allow up to 5 turns for tool calls
                        break
                    done = False
                    # Get current node for this turn (may have changed due to routing)
                    current_node_id = self._current_node.get(session_id)
                    
                    # Update allowed tools for the current node (in case we routed to a new node)
                    node_allowed_tools = None
                    if isinstance(self._agent, AgentSpec) and current_node_id:
                        node_allowed_tools = self._agent.get_node_tools(current_node_id)

                    if self._verbose:
                        _console.rule(
                            f"[bold yellow]Node: {current_node_id}[/bold yellow]"
                        )

                    async with span("provider.stream_decision"):
                        async with measure("provider.stream_decision"):
                            # Augment messages with graph context when available
                            msgs = list(messages_base)
                            if isinstance(self._agent, AgentSpec) and current_node_id:
                                try:
                                    # Get available tool specs from the runner
                                    available_tool_specs = {}
                                    if eff_tool_runner:
                                        all_tools = eff_tool_runner.get_tools()
                                        # Filter to only allowed tools for this node
                                        if node_allowed_tools:
                                            available_tool_specs = {
                                                name: spec
                                                for name, spec in all_tools.items()
                                                if name in node_allowed_tools
                                            }
                                        else:
                                            available_tool_specs = all_tools
                                    
                                    msgs = eff_provider.build_decision_messages(  # type: ignore[union-attr]
                                        self._agent, current_node_id, available_tool_specs, msgs
                                    )
                                except Exception:
                                    msgs = list(messages_base)
                            if self._verbose:
                                _console.print(_format_messages_table(msgs))

                            decision_data = None
                            async for frame in eff_provider.stream_decision(  # type: ignore[union-attr]
                                msgs, schema=payload.get("response_schema")
                            ):
                                # Check pause between frames
                                await self._resume_events[session_id].wait()
                                # Cancel at token/tool boundaries
                                if self._cancel_flags.get(session_id):
                                    self._cancel_flags[session_id] = False
                                    break
                                ftype = frame.get("type")
                                if ftype == EventType.TOKEN_EMITTED:
                                    try:
                                        tf = TokenFrame.model_validate(frame)
                                        data_payload = tf.data
                                    except Exception as exc:  # noqa: BLE001
                                        await self._append(
                                            session_id,
                                            [
                                                SessionEvent(
                                                    session_id=session_id,
                                                    type=EventType.ERROR_OCCURRED,
                                                    data={
                                                        "message": f"invalid token frame: {exc}"
                                                    },
                                                )
                                            ],
                                        )
                                        inc(EventType.ERROR_OCCURRED.value)
                                        break
                                    await self._append(
                                        session_id,
                                        [
                                            SessionEvent(
                                                session_id=session_id,
                                                type=EventType.TOKEN_EMITTED,
                                                data=data_payload,
                                            )
                                        ],
                                    )
                                    inc(EventType.TOKEN_EMITTED.value)
                                    # continue streaming provider frames
                                    continue
                                elif ftype == EventType.DECISION_COMPLETED:
                                    try:
                                        df = DecisionFrame.model_validate(frame)
                                        ddata = df.data
                                    except Exception as exc:  # noqa: BLE001
                                        await self._append(
                                            session_id,
                                            [
                                                SessionEvent(
                                                    session_id=session_id,
                                                    type=EventType.ERROR_OCCURRED,
                                                    data={
                                                        "message": f"invalid decision frame: {exc}"
                                                    },
                                                )
                                            ],
                                        )
                                        inc(EventType.ERROR_OCCURRED.value)
                                        break
                                    await self._append(
                                        session_id,
                                        [
                                            SessionEvent(
                                                session_id=session_id,
                                                type=EventType.DECISION_COMPLETED,
                                                data=ddata,
                                                node_id=self._current_node.get(session_id),
                                            )
                                        ],
                                    )
                                    inc(EventType.DECISION_COMPLETED.value)
                                    decision_data = ddata or {}

                                    if self._verbose:
                                        _console.print(_format_decision(decision_data))

                                    data = decision_data
                                    action = data.get("action")
                                    if action == "RESPOND":
                                        response = data.get("response", "")
                                        assistant_msg = {
                                            "role": "assistant",
                                            "content": [{"type": "text", "data": response}],
                                        }
                                        messages_base.append(assistant_msg)
                                        self._messages[session_id].append(assistant_msg)
                                    if action == "TOOL_CALL":
                                        tool_call = data.get("tool_call", {}) or {}
                                        tool_name = tool_call.get("tool_name")
                                        tool_kwargs = tool_call.get("tool_kwargs", {})
                                        if not eff_tool_runner or not tool_name:
                                            await self._append(
                                                session_id,
                                                [
                                                    SessionEvent(
                                                        session_id=session_id,
                                                        type=EventType.ERROR_OCCURRED,
                                                        data={
                                                            "message": "tool runner not configured or invalid tool call",
                                                            "tool_call": tool_call,
                                                        },
                                                    )
                                                ],
                                            )
                                            inc(EventType.ERROR_OCCURRED.value)
                                            break
                                        
                                        # Add tool call message to history
                                        from nomos.core.schemas import Message
                                        tool_call_msg = Message.tool_call_message(
                                            tool_name, tool_kwargs
                                        ).model_dump()
                                        messages_base.append(tool_call_msg)
                                        self._messages[session_id].append(tool_call_msg)
                                        
                                        # Stream tool frames
                                        ctx = {
                                            "cancel_event": self._cancel_events[session_id],
                                            "session_id": session_id,
                                            "node_id": current_node_id,
                                            "memory": ov.get("memory"),
                                        }
                                        async with span(f"tool.run:{tool_name}"):
                                            async with measure(f"tool.run:{tool_name}"):
                                                if self._verbose:
                                                    _console.print(
                                                        _format_tool_execution(
                                                            tool_name, tool_kwargs
                                                        )
                                                    )

                                                last_result: Any | None = None
                                                async for tframe in eff_tool_runner.run(
                                                    tool_name, tool_kwargs, ctx
                                                ):
                                                    if (
                                                        self._cancel_flags.get(session_id)
                                                        or self._cancel_events[session_id].is_set()
                                                    ):
                                                        self._cancel_flags[session_id] = False
                                                        self._cancel_events[session_id].clear()
                                                        break
                                                    # Convert tool frame to SessionEvent
                                                    # Map tool frame type strings to EventType enum
                                                    frame_type_str = tframe.get(
                                                        "type", "tool.frame"
                                                    )
                                                    try:
                                                        frame_type = EventType(frame_type_str)
                                                    except ValueError:
                                                        # Fallback for unknown types
                                                        frame_type = EventType.ERROR_OCCURRED

                                                    session_event = SessionEvent(
                                                        session_id=session_id,
                                                        type=frame_type,
                                                        data={
                                                            k: v
                                                            for k, v in tframe.items()
                                                            if k != "type"
                                                        },
                                                        node_id=current_node_id,
                                                    )
                                                    await self._append(session_id, [session_event])
                                                    inc(frame_type_str)
                                                    if frame_type_str == "tool.completed":
                                                        last_result = tframe.get("result")
                                                    elif frame_type_str == "tool.error":
                                                        # Tool execution failed - add error message
                                                        error_msg = tframe.get("error", "Unknown error")
                                                        from nomos.core.schemas import Message
                                                        tool_error_msg = Message.tool_error_message(
                                                            tool_name, error_msg
                                                        ).model_dump()
                                                        messages_base.append(tool_error_msg)
                                                        self._messages[session_id].append(tool_error_msg)
                                                        # Clear last_result so we don't add a success message
                                                        last_result = None

                                                # feed tool result back into messages for next turn
                                                if last_result is not None:
                                                    from nomos.core.schemas import Message
                                                    tool_output_msg = Message.tool_output_message(
                                                        tool_name, last_result
                                                    ).model_dump()
                                                    messages_base.append(tool_output_msg)
                                                    self._messages[session_id].append(tool_output_msg)
                                    # Handle routing (MOVE) only on decision frame
                                    if isinstance(self._agent, AgentSpec) and action == "MOVE":
                                        to_id = self._agent.route(
                                            self._current_node.get(session_id) or "", data
                                        )  # type: ignore[arg-type]
                                        if to_id:
                                            await self._append(
                                                session_id,
                                                [
                                                    SessionEvent(
                                                        session_id=session_id,
                                                        type=EventType.ROUTING_APPLIED,
                                                        data={
                                                            "from": self._current_node.get(
                                                                session_id
                                                            ),
                                                            "to": to_id,
                                                            "condition": f"MOVE:{data.get('step_id')}",
                                                        },
                                                    )
                                                ],
                                            )
                                            inc(EventType.ROUTING_APPLIED.value)

                                            if self._verbose:
                                                from_node = self._current_node.get(session_id)
                                                _console.print(
                                                    _format_routing(
                                                        from_node or "",
                                                        to_id,
                                                        f"MOVE:{data.get('step_id')}",
                                                    )
                                                )

                                            self._current_node[session_id] = to_id
                                    # End after one decision turn per input
                                    # End after one decision turn per input (multi-turn handled by client or future loop)
                                    if decision_data and decision_data.get("action") in (
                                        "RESPOND",
                                    ):
                                        done = True
                    if done:
                        break
            except Exception as exc:  # noqa: BLE001
                await self._append(
                    session_id,
                    [
                        SessionEvent(
                            session_id=session_id,
                            type=EventType.ERROR_OCCURRED,
                            data={"message": str(exc)},
                        )
                    ],
                )
                inc(EventType.ERROR_OCCURRED.value)

    async def control(
        self, session_id: str, command: Union[ControlCommand, Dict[str, Any]]
    ) -> None:
        if isinstance(command, dict):
            command = ControlCommand.model_validate(command)
        assert isinstance(command, ControlCommand)
        ctype = command.type
        if ctype == "cancel.requested":
            self._cancel_flags[session_id] = True
            # propagate to tools via cancel event (if in-flight)
            if session_id in self._cancel_events:
                self._cancel_events[session_id].set()
            await self._append(
                session_id,
                [
                    SessionEvent(
                        session_id=session_id,
                        type=EventType.CANCEL_APPLIED,
                        data={"reason": "requested"},
                    )
                ],
            )
            inc(EventType.CANCEL_APPLIED.value)
            return
        if ctype == "pause.requested":
            self._resume_events[session_id].clear()
        elif ctype == "resume.requested":
            self._resume_events[session_id].set()
        elif ctype == "checkpoint.requested":
            from .schemas import Checkpoint

            cid = command.id or str(uuid.uuid4())
            cp = Checkpoint(id=cid, node_id=self._current_node.get(session_id))
            await self._checkpoint_store.save(session_id, cp)
            await self._append(
                session_id,
                [
                    SessionEvent(
                        session_id=session_id,
                        type=EventType.CHECKPOINT_CREATED,
                        data={"id": cid, "node_id": cp.node_id},
                    )
                ],
            )
            inc(EventType.CHECKPOINT_CREATED.value)
            return
        elif ctype == "checkpoint.restore":
            cid_restore: Optional[str] = command.id
            if not cid_restore:
                raise ValueError("checkpoint.restore requires 'id'")
            cp = await self._checkpoint_store.load(session_id, cid_restore)
            self._current_node[session_id] = cp.node_id
            await self._append(
                session_id,
                [
                    SessionEvent(
                        session_id=session_id,
                        type=EventType.CHECKPOINT_RESTORED,
                        data={"id": cid_restore, "node_id": cp.node_id},
                    )
                ],
            )
            inc(EventType.CHECKPOINT_RESTORED.value)
            return
        # default: record control applied
        await self._append(
            session_id,
            [
                SessionEvent(
                    session_id=session_id,
                    type=EventType.CONTROL_APPLIED,
                    data=command.model_dump(),
                )
            ],
        )
        inc(EventType.CONTROL_APPLIED.value)

    async def stream(
        self,
        session_id: str,
        inputs: Optional[Union[SessionInput, Dict[str, Any]]] = None,
    ) -> AsyncIterator[SessionEvent]:
        # If initial inputs provided, enqueue them first
        if inputs:
            if isinstance(inputs, dict):
                inputs = SessionInput.model_validate(inputs)
            assert isinstance(inputs, SessionInput)
            await self.input(session_id, inputs)

        # Ensure a worker is running for this session to process queued inputs
        if session_id not in self._workers:
            self._workers[session_id] = asyncio.create_task(self._worker(session_id))

        # For now, just forward events appended to the store (including inputs/controls)
        async for ev in self._store.subscribe(session_id):
            yield ev

    async def materialize_state(self, session_id: str) -> SessionState:
        events = await self._store.read_by_session(session_id)
        state = SessionState(session_id=session_id)
        # A minimal projection: track last action/token and maintain a small tail
        for ev in events[-50:]:
            state.history_tail.append(ev)
            if ev.type == EventType.DECISION_COMPLETED:
                state.last_action = "decision.completed"
            if ev.type == EventType.TOKEN_EMITTED:
                state.last_action = "io.token"
            if ev.type == EventType.ROUTING_APPLIED:
                state.current_node = ev.data.get("to")
        # if never routed, use initial
        if not state.current_node:
            state.current_node = self._current_node.get(session_id)
        return state

    async def list_events(self, session_id: str) -> List[SessionEvent]:
        """Return the full event list for a session (for debugging/transport)."""
        return await self._store.read_by_session(session_id)
