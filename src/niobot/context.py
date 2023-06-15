import time

import nio
import typing

from .utils.string_view import ArgumentView
from .utils import deprecated

if typing.TYPE_CHECKING:
    from .client import NioBot
    from .commands import Command
    from .attachment import MediaAttachment


__all__ = (
    "Context",
)


class ContextualResponse:
    """Context class for managing replies.

    Usage of this function is not required, however it is a useful utility."""
    def __init__(self, ctx: "Context", response: nio.RoomSendResponse):
        self.ctx = ctx
        self._response = response

    @property
    def message(self) -> nio.RoomMessageText | None:
        """Fetches the current message for this response"""
        result = self.ctx.client.get_cached_message(self._response.event_id)
        if result:
            return result[1]

    async def reply(self, *args) -> "ContextualResponse":
        """
        Replies to the current response.

        This does NOT reply to the original invoking message.

        :param args: args to pass to send_message
        :return: a new ContextualResponse object.
        """

        return ContextualResponse(
            self.ctx, self.ctx.client.send_message(self.ctx.room, *args, reply_to=self._response.event_id)
        )

    async def edit(self, content: str, **kwargs) -> "ContextualResponse":
        """
        Edits the current response.

        :param content: The new content to edit with
        :param kwargs: Any extra arguments to pass to Client.edit_message
        :return: self
        """
        await self.ctx.client.edit_message(
            self.ctx.room,
            self.ctx.message.event_id,
            content,
            **kwargs
        )

    async def delete(self, reason: str = None) -> None:
        """
        Redacts the current response.

        :param reason: An optional reason for the redaction
        :return: None, as there will be no more response.
        """


class Context:
    """Event-based context for a command callback"""
    def __init__(
            self,
            _client: "NioBot",
            room: nio.MatrixRoom,
            event: nio.RoomMessageText,
            command: "Command",
            *,
            invoking_string: str = None
    ):
        self._init_ts = time.time()
        self._client = _client
        self._room = room
        self._event = event
        self._command = command
        self._invoking_string = invoking_string
        to_parse = event.body
        if invoking_string:
            try:
                to_parse = event.body[len(invoking_string):]
            except IndexError:
                to_parse = ""
        self._args = ArgumentView(to_parse)
        self._args.parse_arguments()
        self._original_response = None

    @property
    def room(self) -> nio.MatrixRoom:
        """The room that the event was dispatched in"""
        return self._room

    @property
    def client(self) -> "NioBot":
        """The current instance of the client"""
        return self._client

    bot = client

    @property
    def command(self) -> "Command":
        """The current command being invoked"""
        return self._command

    @property
    def args(self) -> list[str]:
        """Each argument given to this command"""
        return self._args.arguments

    arguments = args

    @property
    def message(self) -> nio.RoomMessageText:
        """The current message"""
        return self._event

    @property
    def original_response(self) -> typing.Optional[nio.RoomSendResponse]:
        """The result of Context.reply(), if it exists."""
        return self._original_response

    msg = event = message

    @property
    def latency(self) -> float:
        """Returns the current event's latency in milliseconds."""
        return self.client.latency(self.event, received_at=self._init_ts)

    @deprecated("Context.respond")
    async def reply(self, *args) -> ContextualResponse:
        """<deprecated, use respond() instead>"""
        return await self.respond(*args)

    async def respond(self, content: str = None, file: "MediaAttachment" = None) -> ContextualResponse:
        """Responds to the invoking message."""
        result = await self.client.send_message(
            self.room,
            content,
            file,
            self.message
        )
        return ContextualResponse(self, result)
