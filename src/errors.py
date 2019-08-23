import io
import traceback
from typing import Iterable

from discord import Embed, DiscordException
from discord.ext.commands import Context, MissingRole, MissingRequiredArgument, CommandNotFound, BadArgument, Bot

from timeout_message import TimeoutMessage


# Handlers
class DiscordExceptionHandler:
    """
    A baseclass for the exception handlers.
    """

    # noinspection PyUnusedLocal
    @staticmethod
    async def handle(ctx: Context, exception: DiscordException):
        """
        Override to handle the exception. Return True if handler execution should be continued.
        Denote the exception type in the type hint.
        """

        # Prepare embed title, part of the description
        embed = Embed(title='⚠ Command error',
                      description=f'There was an error executing the command `{ctx.message.clean_content}`. '
                                  'Please tag @bot_developer and tell them what has happened.')

        # Get the traceback as how it would show in the stdout
        buffer = io.StringIO()
        traceback.print_exception(None, exception, exception.__traceback__, file=buffer)

        # Add the formatted traceback into the embed description,
        # account the current description length and fill the rest
        embed.description += f'```{buffer.getvalue()[-(2000 - len(embed.description)):]}```'

        # Finally send the embed
        await ctx.send(embed=embed)

        # Print to the stderr
        await Bot.on_command_error(ctx.bot, ctx, exception)


class MissingRoleHandler(DiscordExceptionHandler):
    @staticmethod
    async def handle(ctx: Context, exception: MissingRole):
        embed = Embed(
            title='Oops! Missing role.',
            description=f'Only members with the role **{exception.missing_role}** can run the command `{ctx.command}`'
        )

        await TimeoutMessage(ctx, 10).send(embed=embed)


class MissingRequiredArgumentHandler(DiscordExceptionHandler):
    @staticmethod
    async def handle(ctx: Context, exception: MissingRequiredArgument):
        await ctx.send('> Missing required arguments. See below. ⬇ ⬇')
        ctx.bot.help_command.context = ctx
        await ctx.bot.help_command.send_command_help(ctx.command)


class CommandNotFoundHandler(DiscordExceptionHandler):
    @staticmethod
    async def handle(ctx: Context, exception: CommandNotFound):
        await ctx.send(f"> Command `!{ctx.invoked_with}` not found. Type `!help` if you're lost.")


class BadArgumentHandler(DiscordExceptionHandler):
    @staticmethod
    async def handle(ctx: Context, exception: BadArgument):
        await ctx.send(f'> Bad argument given. See below. ⬇ ⬇')
        ctx.bot.help_command.context = ctx
        await ctx.bot.help_command.send_command_help(ctx.command)


class ErrorHandler:
    # Put the error handlers in a order, the top ones will be processed first and have a chance
    # of stopping other handlers to being processed. Putting subclasses before baseclass
    # is recommended
    handlers: Iterable[DiscordExceptionHandler] = (
        CommandNotFoundHandler,
        MissingRoleHandler,
        MissingRequiredArgumentHandler,
        BadArgumentHandler,
        DiscordExceptionHandler
    )

    async def handle(self, ctx: Context, exception: DiscordException):
        """
        Trigger all corresponding handlers for the given exception
        :return: Whether an error handler was triggered.
        """

        # We are iterating because some errors may be subclasses of other errors.
        triggered = False
        for handler in self.handlers:
            if isinstance(exception, handler.handle.__annotations__.get('exception')):
                triggered = True
                if not await handler.handle(ctx, exception):
                    break

        return triggered