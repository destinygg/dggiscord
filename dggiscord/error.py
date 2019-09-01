from config import cfg
from log import logging
import client
import time
import traceback
import sys

logger = logging.getLogger(__name__)
logger.info("loading...")

@client.bot.event
async def on_command_error(ctx, err):

    # ignore common errors we don't care for
    ignored = (client.commands.CommandNotFound, client.commands.UserInputError, client.commands.NoPrivateMessage)
    error = getattr(err, 'original', err)
    if isinstance(error, ignored):
        return

    channel_errlogs = client.bot.get_channel(cfg['discord']['manage_channel'])

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    stack_trace = traceback.format_exception(type(err), err, err.__traceback__)

    msg = """
        Error caught :(
        CMD: `!{1.command}`
        DATE: `{0}`
        SERVER: `{1.message.guild.id}` (`{1.message.guild.name}`)
        CHANNEL: `{1.message.channel.id}` (`#{1.message.channel.name}`)
        INVOKER: `{1.message.author.id}` (`{2}`)
        ```{3}```
        """.format(timestamp, ctx, str(ctx.message.author), "".join(stack_trace))

    # await channel_errlogs.send(msg)

    traceback.print_exception(type(err), err, err.__traceback__, file=sys.stderr)


