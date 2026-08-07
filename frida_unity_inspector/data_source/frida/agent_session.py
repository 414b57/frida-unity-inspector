from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, TypeAlias

from pydantic import ValidationError

from frida_unity_inspector.utils import FridaInjector

from .protocol import CAPABILITY_REQUIRES, EVENT_DATA_ADAPTERS, AgentLoadedData, AgentReadyData, AgentRpc, Capabilities, Events, MessageTypes

logger = logging.getLogger("fui.frida.agent_session")

# (event, protocol-validated event data, optional binary payload)
EventHandler: TypeAlias = Callable[[Events, Any, "bytes | None"], None]


class AgentSession:
    """
    Handles the communication boundary between python-side and agent-side code.
    Allows for easy registration of event handlers and RPC calls to the agent, and ensure incoming messages are validated against the protocol before being dispatched to handlers.
    """

    def __init__(self, injector: FridaInjector) -> None:
        self._injector = injector
        self.rpc = AgentRpc(injector.call)

        self.loaded = asyncio.Event()
        self.ready = asyncio.Event()
        self.capabilities: dict[str, bool] = {}

        self._event_handlers: dict[Events, EventHandler] = {
            # built-in lifecycle events - Handled here for simplicity.
            Events.AGENT_LOADED: self._on_agent_loaded,
            Events.AGENT_READY: self._on_agent_ready,
        }

        injector.register_on_message_callback(self._on_message)

    def close(self) -> None:
        """Stop receiving messages from the injector."""
        self._injector.unregister_on_message_callback(self._on_message)

    # state 
    def has_capability(self, capability: Capabilities | str) -> bool:
        """Whether the agent detected `capability` as available. False until the agent is ready."""
        return self.capabilities.get(capability, False)

    def missing_requirements(self, capability: Capabilities | str) -> tuple[Capabilities, ...]:
        """The capabilities `capability` declares as requirements that the agent reported unavailable. Empty if it has none, or all are met."""
        try:
            key = Capabilities(capability)
        except ValueError:
            return ()
        return tuple(required for required in CAPABILITY_REQUIRES.get(key, ()) if not self.has_capability(required))

    def register_event_handler(self, event: Events, handler: EventHandler) -> None:
        """Route `event` to `handler`, replacing any existing route for it."""
        self._event_handlers[event] = handler
    
    # helper
    def call_capability(self, capability: Capabilities | str, *args: Any, **kwargs: Any) -> Any:
        """Call an agent RPC method, but only if the agent has the given capability."""
        if not self.has_capability(capability):
            missing = self.missing_requirements(capability)
            reason = f" - it requires {', '.join(missing)}, which the agent does not have" if missing else ""
            raise RuntimeError(f"Agent does not have capability '{capability}'{reason}")
        return self.rpc.dispatch(capability, *args, **kwargs)

    # message routing 
    def _on_message(self, message: dict[str, Any], data: bytes | None) -> None:
        """Entry point for every message the injector receives from the agent."""
        logger.trace(f"Received message from agent: {message}, data length: {len(data) if data else 0}")
        msg_type = message.get("type", None)
        if msg_type == "send":
            self._handle_send(message, data)
        elif msg_type == "error":
            # frida wraps uncaught agent-side exceptions in an 'error' message.
            logger.error(f"Agent raised an error: {message.get('description')}")
            logger.debug(f"Agent stack: {message.get('stack')} | Message: {message} | Data: {data}")
        else:
            logger.warning(f"Received message with unrecognized type '{msg_type}' from agent.")
            logger.debug(f"Message: {message} | Data: {data}")

    def _handle_send(self,  message: dict[str, Any], data: bytes | None) -> None:
        """Handle the payload of a 'send' message from the agent."""
        payload = message.get("payload", None)
        if not isinstance(payload, dict):
            logger.warning("Received 'send' message without a dict 'payload' from agent.")
            logger.debug(f"Message: {message} | Payload: {payload} | Data: {data}")
            return
        message_type = payload.get("type", None)
        if message_type == MessageTypes.EVENT:
            self._handle_event(payload.get("event", None), payload.get("data", None), data)
        else:
            logger.warning(f"Received 'send' message with unrecognized type '{message_type}' from agent.")
            logger.debug(f"Payload: {payload} | Data: {data}")

    def _handle_event(self, event_name: Any, event_data: Any, data: bytes | None) -> None:
        """Validate an event against the protocol and dispatch it to its handler."""
        logger.trace(f"Handling event '{event_name}' with data: {event_data}")
        try:
            event = Events(event_name)
        except ValueError:
            logger.warning(f"Received unknown event '{event_name}' from agent.")
            logger.debug(f"Event data: {event_data} | Data: {data}")
            return

        try:
            event_data = EVENT_DATA_ADAPTERS[event].validate_python(event_data)
        except ValidationError as e:
            logger.error(f"Event '{event}' from agent has an unexpected payload: {e}")
            logger.debug(f"Event data: {event_data} | Data: {data}")
            return

        handler = self._event_handlers.get(event, None)
        if handler is None:
            logger.warning(f"No handler registered for event '{event}'.")
            logger.debug(f"Event data: {event_data} | Data: {data}")
            return
        handler(event, event_data, data)

    # built-in lifecycle handlers 
    def _on_agent_loaded(self, event: Events, event_data: AgentLoadedData, data: bytes | None) -> None:
        self.loaded.set()
        logger.info("Frida agent loaded successfully.")

    def _on_agent_ready(self, event: Events, event_data: AgentReadyData, data: bytes | None) -> None:
        self.capabilities = event_data
        self.ready.set()
        logger.info(f"Frida agent is ready. Detected capabilities: {event_data}")
