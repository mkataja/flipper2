import logging
import re
import threading
import time

from irc import bot
import irc

import config
from message import Message
import modules.modulelist


class FlipperBot(bot.SingleServerIRCBot):
    def __init__(self):
        self.last_pong = None
        self.nick_tail = ""
        
        bot.SingleServerIRCBot.__init__(self, 
                                        [(config.SERVER, config.PORT)], 
                                        config.NICK, 
                                        config.REALNAME,
                                        config.RECONNECTION_INTERVAL)
        
        irc.client.ServerConnection.buffer_class = irc.buffer.LenientDecodingLineBuffer
        
        self._registered_modules = [m(self) for m in modules.modulelist.MODULES]
    
    def _dispatcher(self, connection, event):
        super()._dispatcher(connection, event)
        
        for module in self._registered_modules:
            method = getattr(module, "on_" + event.type, None)
            if method is not None:
                threading.Thread(target=method, 
                                 args=(connection, event)).start()
        
    def _keep_alive(self):
        if not self.connection.is_connected():
            self.last_pong = None
            return
        
        self.connection.ping("keep-alive")
        
        current_time = time.time()
        logging.debug("Last pong at {}, current time {}".format(self.last_pong,
                                                                current_time))
        if (self.last_pong is not None and 
                current_time > self.last_pong + config.KEEP_ALIVE_TIMEOUT):
            self.last_pong = None
            self.jump_server("Timeout")
    
    def _keep_nick(self):
        if not self.connection.is_connected():
            self.nick_tail = ""
            return
        
        if self.nick_tail != "":
            self.nick_tail = ""
            logging.debug("Trying to change nick from {} to {}".format(
                self.connection.get_nickname(), config.NICK))
            self.connection.nick(config.NICK)
    
    def on_welcome(self, connection, event):
        self.reactor.execute_every(config.KEEP_ALIVE_FREQUENCY, 
                                   self._keep_alive, ())
        self.reactor.execute_every(60, self._keep_nick, ())
        
        for channel in config.CHANNELS:
            connection.join(channel)
        
    def on_pong(self, connection, event):
        self.last_pong = time.time()
    
    def on_nicknameinuse(self, connection, event):
        self.nick_tail = self.nick_tail + "_"
        connection.nick(config.NICK + self.nick_tail)
        
    def on_privmsg(self, connection, event):
        self._handle_command(connection, event, True)
        
    def on_pubmsg(self, connection, event):
        self._handle_command(connection, event, False)
    
    def _handle_command(self, connection, event, is_private_message):
        message = Message(self, connection, event, is_private_message)
        logging.debug("handling privmsg: {}".format(message))
        threading.Thread(target=message.run_command).start()
    
    def safe_privmsg(self, target, message):
        if not self.connection.is_connected():
            logging.debug("Tried to send privmsg while disconnected: aborting")
            return
        text = re.sub(r"(\r?\n|\t)+", " ", message)
        self.connection.privmsg(target, text)
