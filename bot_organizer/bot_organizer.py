# Licenced under MIT license
# So you can use it as you want, but no warranty from us ;)

"""
This is a rather simple bot for popular messenger Telegram.
It provides some simple functionality for timers and events set
and uses telegram-python-api for communicating with user in Telegram.

Main purpose of the bot was to learn telegram-python-api, how to use git,
write tests in pytest, use travis and generate docs with sphinx.

Writen by Artemii Hrynevych and Mateusz Tarasek.
"""

import logging
from datetime import datetime
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, 
                          RegexHandler, ConversationHandler)

#------------------------------------------------------------------------------
# Global variables + general functions.
#------------------------------------------------------------------------------

TOKEN_FILENAME = 'TOKEN.txt' # replace with the path to the file with token to your bot
EVENT_NAME, EVENT_DATE, EVENT_LOC, EVENT_MSG = range(4)
TIMER_NAME, TIMER_DUE, TIMER_MSG = range(4, 7)

LEE = 'last_event_entry'
LTE = 'last_timer_entry'
NAME = 'name'
DUE = 'due'
DATE = 'date'
LOC = 'location'
MSG = 'message'
FIELDS = {LEE: {NAME, DATE, LOC, MSG},
          LTE: {NAME, DUE, MSG}}
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M:%S'
DATE_TIME_FORMAT = ' '.join((DATE_FORMAT, TIME_FORMAT))
JOB_STR_END = '_job'

start_reply_keyboard = [['/event','/timer'], ['/cancel','/help']]
start_markup = ReplyKeyboardMarkup(start_reply_keyboard, one_time_keyboard=False)


def get_logger():
    """ 
    Function to get logger instance. Since loggers are hashed it actually
    is pretty fast and doesn't consume a lot of memory.
    Also it makes logging easier for testing, since we can patch get_logger
    """
    return logging.getLogger(__name__)


def read_token(filename):
    """
    Very simple function to get token for your bot from a file
    """
    with open(filename, 'r') as file:
        token = file.readline().strip()
        return token

#------------------------------------------------------------------------------
# Code block for the event conversation handler.
#------------------------------------------------------------------------------


def event(_bot, update, chat_data):
    """
    New event entry start function

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param chat_data: Dict that contains chat specific data.

    :return: EVENT_NAME token for conversation handler to move on.
    """
    chat_data[LEE] = {NAME: None, DATE: None,
                      LOC: None, MSG: None}
    user = update.message.from_user
    get_logger().info(f'{user.first_name} started new event entry.')
    update.message.reply_text('Ok.Let\'s create new event!\n'
                              'Send /cancel to cancel the command.\n'
                              'Enter the name of the event you want '
                              'me to write down:')
    return EVENT_NAME


def event_name(_bot, update, chat_data):
    """
    Function to save event name and ask for event date
    in the event conversation.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param chat_data: Dict that contains chat specific data.

    :return: EVENT_DATE token for conversation handler to move on.
    """
    user = update.message.from_user
    chat_data[LEE][NAME] = update.message.text
    get_logger().info(f'{user.first_name}\'s event name: {update.message.text}')
    update.message.reply_text(f'Ok. Now, please, enter the date and time of the:'
                              f'{update.message.text}\nPlease, enter date in the'
                              f'"{DATE_TIME_FORMAT}" format!')
    return EVENT_DATE


def event_date(_bot, update, chat_data):
    """
    Function to save event date and ask for event location.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param chat_data: Dict that contains chat specific data.

    :return: EVENT_DATE token if data was not correct.
    :return: EVENT_LOC token for conversation handler to move on.
    """
    user = update.message.from_user

    try:
        event_date = datetime.strptime(update.message.text.strip(),
                                       DATE_TIME_FORMAT)
        if event_date < datetime.now():
            update.message.reply_text('Sorry we can not go back to future!')
            raise ValueError
    except ValueError:
        get_logger().error(f'{user.first_name}\'s {chat_data[LEE][NAME]} '
                     f'entered wrong date: {update.message.text}')
        update.message.reply_text(f'Please, enter date in the '
                                  f'"{DATE_TIME_FORMAT}" format!')
        return EVENT_DATE

    chat_data[LEE][DATE] = event_date
    get_logger().info(f'{user.first_name}\'s {chat_data[LEE][NAME]} date: {event_date}')
    update.message.reply_text('Done! Now send me the location of the event'
                              ' or /skip:\n')
    return EVENT_LOC


def skip_event_loc(_bot, update):
    """
    Function to handle event location skip

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.

    :return: EVENT_MSG token for conversation handler to move on.
    """
    user = update.message.from_user
    get_logger().info(f'{user.first_name} did not send a location of the event.')
    update.message.reply_text('Ok! Now send me the message you want me to send '
                              'to you as a reminder for the event or /skip:\n')
    return EVENT_MSG


def event_loc(_bot, update, chat_data):
    """Function to save event location and ask for event message.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param chat_data: Dict that contains chat specific data.

    :return: EVENT_MSG token for conversation handler to move on.
    """
    user = update.message.from_user
    get_logger().info(f'{user.first_name}\'s location of the {chat_data[LEE][NAME]}:'
                f' {update.message.text}')
    chat_data[LEE][LOC] = update.message.text
    update.message.reply_text('Ok! I\'ve writen down location of the event!\n'
                              'Now send me the message you want me to send you'
                              'as a reminder for the event or /skip:\n')
    return EVENT_MSG


def skip_event_msg(_bot, update, job_queue, chat_data):
    """
    Function to handle event message skip and set up event.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param job_queue: queue of jobs for invoking functions after some time.

    :return: ConversationHandler.END token to end the conversation.
    """
    user = update.message.from_user
    get_logger().info(f'{user.first_name} did not send a message for the event.')
    update.message.reply_text('Done! I wrote down all the info about the event!')

    set_event(update, job_queue, chat_data)
    return ConversationHandler.END


def event_msg(_bot, update, job_queue, chat_data):
    """
    Function to save event message and set up event.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param job_queue: queue of jobs for invoking functions after some time.
    :param chat_data: Dict that contains chat specific data.

    :return: ConversationHandler.END token to end the conversation.
    """
    user = update.message.from_user
    get_logger().info(f'{user.first_name}\'s message for the {chat_data[LEE][NAME]}:'
                '\n {update.message.text}')
    chat_data[LEE][MSG] = update.message.text
    update.message.reply_text('Done! I wrote down all the info about the event!')

    set_event(update, job_queue, chat_data)
    return ConversationHandler.END


def cancel_event(_bot, update):
    """
    Function to handle new event entry cancel

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.

    :return: ConversationHandler.END token to end the conversation.    
    """
    user = update.message.from_user
    get_logger().info(f'User {user.first_name} canceled the new event.')
    update.message.reply_text('Ok, I canceled the new event entry!')
    return ConversationHandler.END
#--------------------------------------------------------------------------------
# End of the code block for the event conversation handler.
#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------
# Code block for the timer conversation handler.
#--------------------------------------------------------------------------------


def timer(_bot, update, chat_data):
    """
    New timer entry start function

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param chat_data: Dict that contains chat specific data.

    :return: TIMER_NAME token for conversation handler to move on.
    """
    chat_data[LTE] = {NAME: None, DUE: None,
                      MSG: None}

    user = update.message.from_user
    get_logger().info(f'{user.first_name} started new event entry.')
    update.message.reply_text('Ok.Let\'s create new timer!\n'
                              'Send /cancel to cancel the command.\n'
                              'Enter the name of the timer:')
    return TIMER_NAME


def timer_name(_bot, update, chat_data):
    """
    Function to save timer name and ask for timer due
    in the timer conversation.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param chat_data: Dict that contains chat specific data.

    :return: TIMER_DUE token for conversation handler to move on.
    """
    user = update.message.from_user
    chat_data[LTE][NAME] = update.message.text
    get_logger().info(f'{user.first_name}\'s timer name: {update.message.text}')
    update.message.reply_text(f'Ok. Now, please, enter the due of the timer:'
                              ' "HH:MI:SS" format!')
    return TIMER_DUE


def timer_due(_bot, update, chat_data):
    """
    Function to save timer due and ask for timer message.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param chat_data: Dict that contains chat specific data.

    :return: TIMER_DUE token if due was not correct to get timer due again.
    :return: TIMER_MSG token if due was ok for conversation handler to move on.
    """

    user = update.message.from_user

    try:

        _due = update.message.text.strip().split(":")
        if len(_due) != 3:
            raise ValueError
        _due = int(_due[0]) * 3600 + int(_due[1]) * 60 + int(_due[2])

    except ValueError:
        get_logger().error(f'{user.first_name}\'s {chat_data[LTE][NAME]} '
                    f'entered wrong due: {update.message.text}')
        update.message.reply_text('Please, enter due in the '
                                  '"HH:MI:SS" format!')
        return TIMER_DUE

    chat_data[LTE][DUE] = _due
    get_logger().info(f'{user.first_name}\'s {chat_data[LTE][NAME]} due: {_due}')
    update.message.reply_text('Done! Now send me the message you want me to send you'
                              'as a reminder for the event or /skip:\n')

    return TIMER_MSG


def timer_msg(_bot, update, job_queue, chat_data):
    """
    Function to save timer message and set up timer.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param job_queue: queue of jobs for invoking functions after some time.
    :param chat_data: Dict that contains chat specific data.


    :return: ConversationHandler.END token to end the conversation.
    """

    user = update.message.from_user
    get_logger().info(f'{user.first_name}\'s message for the {chat_data[LTE][NAME]}:'
                '\n {update.message.text}')
    chat_data[LTE][MSG] = update.message.text
    update.message.reply_text('Done! I wrote down all the info about the timer!')

    set_timer(update, job_queue, chat_data)
    return ConversationHandler.END


def skip_timer_msg(_bot, update, job_queue, chat_data):
    """
    Function to handle timer message skip and set up timer.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param job_queue: queue of jobs for invoking functions after some time.
    :param chat_data: Dict that contains chat specific data.


    :return: ConversationHandler.END token to end the conversation.
    """

    user = update.message.from_user
    get_logger().info(f'{user.first_name} did not send a message for the timer.')
    update.message.reply_text('Done! I wrote down all the info about the timer!')

    set_timer(update, job_queue, chat_data)
    return ConversationHandler.END


def cancel_timer(_bot, update):
    """Function to handle new timer entry cancel

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.

    :return: ConversationHandler.END token to end the conversation.
    """
    user = update.message.from_user
    get_logger().info(f'User {user.first_name} canceled the new timer.')
    update.message.reply_text('Ok, I canceled the new timer entry!')
    return ConversationHandler.END

#--------------------------------------------------------------------------------
# End of the code block for the timer conversation handler.
#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------
# Setters for event and timer code block + notification generator code block
#--------------------------------------------------------------------------------


def set_event(update, job_queue, chat_data):
    """
    Function to set up event notification job.
    
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param job_queue: queue of jobs for invoking functions after some time.
    :param chat_data: Dict that contains chat specific data.
    """
    event_name = chat_data[LEE][NAME]
    event_job_name = event_name+JOB_STR_END
    user = update.message.from_user
    
    if event_job_name in chat_data:
        update.message.reply_text(f'Updating \'{event_name}\' entry')
        event_job = chat_data[event_job_name]
        event_job.schedule_removal()

    if chat_data[LEE][DATE] > datetime.now():
        event_job = job_queue.run_once(alarm, when=chat_data[LEE][DATE],
                                       context=[
                                           update.message.chat_id,
                                           event_name, 
                                           event_notif_str(chat_data[LEE])
                                       ]
                                      )
        chat_data[event_job_name] = event_job
        get_logger().info(f'{user.first_name} set up new event {chat_data[LEE][NAME]}!')
        update.message.reply_text(f'Event {chat_data[LEE][NAME]} successfully set!')    
    else:
        get_logger().error(f'{user.first_name} for event: '
                           f'{chat_data[LEE][NAME]} entered uncorrect date!')
        update.message.reply_text('Sorry we can not go back to future!')

    del chat_data[LEE]
            
def event_notif_str(event_dict):
    """
    Function to build event notification string.
    
    :param event_dict: dict that contains name, date, loc and msg for event.

    :return: notification string.
    """
    notif = ''.join(('Event: ', event_dict[NAME]))
    notif = ''.join((notif, '\nDate: ',
                     event_dict[DATE].strftime(DATE_TIME_FORMAT)))
    if event_dict[LOC] is not None:
        notif = ''.join((notif, '\nLocation: ', event_dict[LOC]))
    if event_dict[MSG] is not None:
        notif = ''.join((notif, '\nMessage: ', event_dict[MSG]))
    return notif

#------------------------------------------------------------------------------
# One message event setting.
#------------------------------------------------------------------------------


def new_event(_bot, update, args, job_queue, chat_data):
    """
    Handler for one message event set.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param args: Arguments for new event (name, date, loc, msg)
    :param job_queue: Queue of jobs for invoking functions after some time.
    :param chat_data: Dict that contains chat specific data.
    """
    # check mandatory arguments: event_date and event_name
    user = update.message.from_user
    try:
        date = args[0]
        time = args[1]
        event_date = datetime.strptime(
            ' '.join((date, time)), DATE_TIME_FORMAT)
        if event_date < datetime.now():
            update.message.reply_text('Sorry we can not go back to future!')
            raise ValueError
        event_name = args[2]
    # if mandatory arguments are absent or not valid
    except (IndexError, ValueError):
        get_logger().error(f'{user.first_name} entered wrong args'
                           f' for one message event setting: {args}')
        update.message.reply_text(f'Usage:/new_event <date_time "{DATE_TIME_FORMAT}">'
                                   '<event_name> [event_loc] [event_msg]\n'
                                   'All data must be in the correct order!')
        # not valid command - exit the function
        return
    # adding optional arguments
    event_loc = None
    if args[3:]:
        event_loc = args[3]
    event_msg = None
    if args[4:]:
        event_msg = ' '.join(args[4:])
    # adding info aboud event to chat data dict as 'last_event_entry'
    chat_data[LEE] = dict()
    chat_data[LEE][NAME] = event_name
    chat_data[LEE][DATE] = event_date
    chat_data[LEE][LOC] = event_loc
    chat_data[LEE][MSG] = event_msg
    # set up the job_queue notification for the event
    set_event(update, job_queue, chat_data)

#------------------------------------------------------------------------------
# Setter for timer + notification generator code block
#------------------------------------------------------------------------------


def set_timer(update, job_queue, chat_data):
    """
    Function to set up new timer notification job.
    
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param job_queue: queue of jobs for invoking functions after some time.
    :param chat_data: Dict that contains chat specific data.
    """
    timer_name = chat_data[LTE][NAME]
    timer_job_name = timer_name+JOB_STR_END
    user = update.message.from_user
    
    if timer_job_name in chat_data:
        update.message.reply_text(f'Updating \'{timer_name}\' entry')
        timer_job = chat_data[timer_job_name]
        timer_job.schedule_removal()
    
    timer_job = job_queue.run_once(alarm, chat_data[LTE][DUE], 
                               context=[
                                   update.message.chat_id,
                                   timer_name,
                                   timer_notif_str(chat_data[LTE])
                               ]
                              )
    chat_data[timer_job_name] = timer_job
    get_logger().info(f'User {user.first_name} set up new timer {timer_name} '
                f'for {chat_data[LTE][DUE]} seconds.')
    update.message.reply_text(f'Timer {chat_data[LTE][NAME]} successfully set!')    
    del chat_data[LTE]


def timer_notif_str(timer_dict):
    """
    Function to build timer notification string.
    
    :param timer_dict: dict with name and message for timer.
    :return: notification string.
    """
    notif = ''.join(('Timer: ', timer_dict[NAME]))
    if timer_dict[MSG] is not None:
        notif = ''.join((notif, '\nMessage: ', timer_dict[MSG]))
    return notif

#------------------------------------------------------------------------------
# One timer event setting.
#------------------------------------------------------------------------------

def new_timer(_bot, update, args, job_queue, chat_data):
    """
    Handler for one line timer set.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param args: Arguments for new timer (name, due, msg)
    :param job_queue: queue of jobs for invoking functions after some time.
    :param chat_data: Dict that contains chat specific data.
    """
    user = update.message.from_user

    try:
        # args[1] should contain the name of the timer
        timer_name = args[1]
    except IndexError:
        timer_name = 'timer'

    # check for only mandatory argument - timer due
    try:
        # args[0] should contain the time for the timer in seconds
        timer_due = int(args[0])
        if timer_due < 0:
            update.message.reply_text('Sorry we can not go back to future!')
            raise ValueError
    except (IndexError, ValueError):
        get_logger().error(f'{user.first_name}\'s {timer_name} '
                           f'entered wrong timer due: {update.message.text}')
        update.message.reply_text(
            'Usage: /new_timer <seconds> [timer_name] [timer_message]')
        return

    timer_msg = None
    if args[2:]:
        timer_msg = ' '.join(args[2:])
    # adding info about event to chat data dict as 'last_timer_entry'
    chat_data[LTE] = dict()
    chat_data[LTE][NAME] = timer_name
    chat_data[LTE][DUE] = timer_due
    chat_data[LTE][MSG] = timer_msg
    # set up the job_queue notification for the event
    set_timer(update, job_queue, chat_data)
#------------------------------------------------------------------------------
# General bot functionality
#------------------------------------------------------------------------------

def start(_bot, update):
    """
    Function for start command handler.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    """
    update.message.reply_text('Hi! I\'m organizer helper bot!\n'
                              'Write /help to see all available commands.',
                              reply_markup=start_markup)

def help(_bot, update):
    """
    Function for help command handler.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    """
    update.message.reply_text('Currently you can use only:\n'
                              '/new_timer <seconds> [timer_name] [timer_message]'
                              ' - to set timer.\n'
                              f'/new_event <date "{DATE_FORMAT}"> <time "{TIME_FORMAT}">'
                              '<event_name> [event_loc] [event_msg]'
                              ' - to create an new event.\n'
                              '/event to create new event using conversation'
                              ' handler.\n'
                              '/timer to create new timer using conversation'
                              ' handler.\n'
                              '/unset <name> to unset timer/event.')

def alarm(bot, job):
    """
    Function to send alarm notification message to the user
    who set up the event or timer.

    :param bot: bot object will send the message from the job.
    :param job: job object contains the chat_id and message in job.context.
    """
    chat_id = job.context[0]
    # job_event_name = job.context[1]
    job_message = job.context[2]
    bot.send_message(chat_id, text=job_message)

#------------------------------------------------------------------------------
# Unset, error and unknown commands handlers.
#------------------------------------------------------------------------------


def unset(_bot, update, args, chat_data):
    """
    Remove the job if the user changed their mind.
    
    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param args: Message as a list. Should contain job name to unset.
    :param chat_data: Dict that contains chat specific data.
    """
    try:
        job_name = ''.join((args[0], JOB_STR_END))
    except IndexError:
        job_name = ''.join(('timer', JOB_STR_END))
        
    if job_name not in chat_data:
        update.message.reply_text(f'You have no active {job_name}.')
        return
    
    job = chat_data[job_name]
    job.schedule_removal()
    del chat_data[job_name]
    update.message.reply_text(f'{job_name} successfully unset!')


def error(_bot, update, error):
    """
    Log Errors caused by Updates.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: Contains event data, such as user_id, chat_id, text sent.
    :param error: error which caused invocation of this function.
    """
    get_logger().warning(f'Update "{update}" caused error "{error}"')


def unknown(_bot, update):
    """
    Function for unknown command handler.

    :param _bot: Not used, required only by telegram-bot api.
    :param update: update which triggered this handler.
    """
    update.message.reply_text('Sorry, I didn\'t understand that command.')

#------------------------------------------------------------------------------
# Main function for bot to be run on a computer.
#------------------------------------------------------------------------------


def main():
    """
    Main function to initialize bot, add all handlers and start listening
    to the user's input.
    """
    updater = Updater(read_token(TOKEN_FILENAME))
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('new_timer', new_timer,
                                          pass_args=True,
                                          pass_job_queue=True,
                                          pass_chat_data=True))
    dispatcher.add_handler(CommandHandler('new_event', new_event,
                                          pass_args=True,
                                          pass_job_queue=True,
                                          pass_chat_data=True))
    dispatcher.add_handler(CommandHandler('unset', unset,
                                          pass_args=True,
                                          pass_chat_data=True))
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('event', event, pass_chat_data=True),
                      CommandHandler('timer', timer, pass_chat_data=True)
                      ],

        states={
            EVENT_NAME: [MessageHandler(Filters.text, event_name, pass_chat_data=True)],
            EVENT_DATE: [MessageHandler(Filters.text, event_date, pass_chat_data=True)],
            EVENT_LOC: [MessageHandler(Filters.text, event_loc, pass_chat_data=True),
                        CommandHandler('skip', skip_event_loc)],
            EVENT_MSG: [MessageHandler(Filters.text, event_msg,
                                       pass_job_queue=True, pass_chat_data=True),
                        CommandHandler('skip', skip_event_msg, 
                                       pass_job_queue=True, pass_chat_data=True)],
            TIMER_NAME: [MessageHandler(Filters.text, timer_name, pass_chat_data=True)],
            TIMER_DUE: [MessageHandler(Filters.text, timer_due, pass_chat_data=True)],
            TIMER_MSG: [MessageHandler(Filters.text, timer_msg,
                                       pass_job_queue=True, pass_chat_data=True),

            CommandHandler('skip', skip_timer_msg,
                           pass_job_queue=True, pass_chat_data=True)]
        },

        fallbacks=[CommandHandler('cancel', cancel_event),
                   CommandHandler('event', event, pass_chat_data=True),
                   CommandHandler('timer', timer, pass_chat_data=True)
                   ]
    )
    
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))
    # log all errors
    dispatcher.add_error_handler(error)
    # Start the Bot
    updater.start_polling()
    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the _bot gracefully.
    updater.idle()


if __name__=='__main__':
    # Enable logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    main()
