import logging
from typing import Coroutine

from discord import Message, NotFound, RawReactionActionEvent
from discord.ext.commands import Context

logger = logging.getLogger('ReactCallbackMng')


class ReactionCallbackManager:
    """
    Allows message reactions to act like buttons to the user.

    The class manages all the reactions an callbacks, including the cleanup.

    Note:
        Make sure to `await` the `asyncinit` method right after initialization.

    Attributes:
        ctx (discord.ext.commands.Context): The context of the message to
            manage.
        msg (discord.Message): The message to manage.
        callbacks (dict): A dictionary of unicode emoji codes and its callbacks.
    """

    ctx: Context
    msg: Message
    callbacks: dict

    TAG = 'ReactTriggerMngr'

    def __init__(self, ctx: Context, msg: Message, callbacks: dict):
        """ The arguments are the same as the class attributes. """
        self.ctx = ctx
        self.msg = msg
        self.callbacks = callbacks

    # TODO is it really required, or can we use create_task()?
    async def asyncinit(self):
        """ Add the reactions and the listener. """
        # Add reactions
        for reaction in self.callbacks:
            await self.msg.add_reaction(reaction)

        # Add listener
        self.ctx.bot.add_listener(self.on_raw_reaction_add)

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        # Internal use

        # Have to cook the raw reaction myself, because the cache in discord py
        # is kinda broken :(

        # Skip other messages and other users
        if (payload.message_id != self.msg.id
                or payload.user_id != self.ctx.author.id):
            return

        # Execute callback
        callback = self.callbacks.get(payload.emoji.name)
        if callback:
            try:
                await callback()
            except CancelCallback:
                logger.warning(f'Cancelled callback `{callback.__name__}` {callback}')

        # Remove reaction
        await self.msg.remove_reaction(payload.emoji,
                                       self.ctx.bot.get_user(payload.user_id))

    async def listen_for(self, reaction: str, callback: Coroutine):
        if reaction not in self.callbacks:
            try:
                await self.msg.add_reaction(reaction)
            except NotFound:
                logger.warning(f'Tried adding {reaction} on non-existing message!')

        self.callbacks[reaction] = callback

    async def remove_listen_for(self, reaction: str):
        if reaction not in self.callbacks:
            return

        try:
            await self.msg.remove_reaction(reaction, self.ctx.bot.user)
        except NotFound:
            logger.warning(f'Tried removing {reaction} on non-existing message!')

        self.callbacks.pop(reaction)

    async def cleanup(self):
        """ Remove all the reactions and the listener. """
        # Clear reactions
        await self.msg.clear_reactions()

        # Remove listener
        self.ctx.bot.remove_listener(self.on_raw_reaction_add)


class CancelCallback(Exception):
    """
    Raise when task execution of ReactionCallbackManager has to be cancelled.
    Only this exception will be caught and warning will be logged.
    """
