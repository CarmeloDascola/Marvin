import asyncio
import gc
import inspect
import time

from discord import Embed, NotFound, Role
from discord.ext import tasks
from discord.ext.commands import Context

from cache import Cache
from logger import Logger
from timeout_message import TimeoutMessage


def del_invoc(fn: callable):
    """
    Delete the commands invocation message after the command has been
    successfully executed.
    """

    async def wrapper(self, ctx: Context, *args, **kw):
        ret = await fn(self, ctx, *args, **kw)
        if not hasattr(ctx, 'is_private'):  # For command panel
            try:
                await ctx.message.delete()
            except NotFound:
                pass

        return ret

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    wrapper.__signature__ = inspect.signature(fn)

    return wrapper


def list_subcommands(fn: callable):
    """ List all the subcommands to the user if no subcommand was invoked. """

    async def wrapper(self, ctx: Context, *args, **kw):
        if not ctx.invoked_subcommand:
            _e = Embed(title='Available subcommands',
                       description=', '.join(
                           map(lambda x: f'`{x.name}`', ctx.command.commands)))
            await TimeoutMessage(ctx, 5).send(embed=_e)

        return await fn(self, ctx, *args, **kw)

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    wrapper.__signature__ = inspect.signature(fn)

    return wrapper


def required_role(role_id: int):
    """ Execute only when the user meets the role requirements. Otherwise, inform him. """

    def decorator(fn: callable):
        async def wrapper(self, ctx: Context, *args, **kw):
            req_role: Role = ctx.guild.get_role(role_id)
            if req_role not in ctx.author.roles:
                embed = Embed(title='⚠ Invalid role!',
                              description=('You do not meet the role requirements. '
                                           f'This command is for **{req_role.name}** users only. '
                                           'Your command will not be executed.'))
                await TimeoutMessage(ctx, 5).send(embed=embed)
                return

            return await fn(self, ctx, *args, **kw)

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        wrapper.__signature__ = inspect.signature(fn)

        return wrapper

    return decorator


def start_when_needed(*args, **kw):
    """
    When the bot is shut down, none of the loops will remember when it was executed the last time. This decorator
    will make it so the loop is started only when the interval would elapse, so no resources are wasted. Do not use
    in classes that you will be creating more instances of, since that will lead to fake instance injection!

    :param args: The args to use when starting the loop.
    :param kw: The kwargs to use when starting the loop.
    """

    def decorator(loop: tasks.Loop):
        # Inject an instance of the class when instantiated to the loop
        _current_frame = inspect.currentframe()
        _outer_frames = inspect.getouterframes(_current_frame, 0)
        class_name = _outer_frames[1].function

        coro_name = loop.coro.__name__
        cache_key = '__last_time_started__' + coro_name

        # Create a wrapper that stores the last execution time
        old_coro = loop.coro

        # noinspection PyShadowingNames,PyProtectedMember
        async def coro(*args, **kw):
            # Inject the instance if the class the decorated method belongs to
            if not loop._injected:
                for obj in gc.get_objects():
                    try:
                        if obj.__class__.__name__ == class_name:
                            loop._injected = obj
                            break
                    except AttributeError:
                        pass

            # Add the injected instance to args
            if loop._injected and loop._injected not in args:
                args = [loop._injected] + list(args)

            _time = time.time()  # Store the start of the execution time
            await old_coro(*args, **kw)
            Cache.cache(cache_key, _time)  # Save the time

        loop.coro = coro
        loop.coro.__name__ = coro_name

        # Schedule the loop start
        # noinspection PyProtectedMember
        cache = Cache._read_cache()
        entry = cache.get(cache_key)

        if not entry:
            loop.start(*args, **kw)
            Logger.info(f'LoopStarter: {loop.coro.__name__} will be started immediately.')
            return loop

        last_executed = int(entry.get('stamp', 0))
        # noinspection PyProtectedMember
        will_expire_at = last_executed + loop._sleep
        will_last_seconds = will_expire_at - int(time.time())

        async def starter():
            await asyncio.sleep(will_last_seconds)
            loop.start()

        Logger.info(f'LoopStarter: {loop.coro.__name__} was scheduled to start in {will_last_seconds} seconds.')
        loop.loop.create_task(starter())

        return loop

    return decorator