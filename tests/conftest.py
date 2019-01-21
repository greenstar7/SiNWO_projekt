import pytest
from bot_organizer import bot_organizer as bo
from datetime import datetime, timedelta

@pytest.fixture
def get_logger(mocker):
    return mocker.patch('bot_organizer.bot_organizer.get_logger')()

@pytest.fixture(name='bot', scope='module')
def _bot():
    return object()

@pytest.fixture(name='event_chat_data', scope='function')
def _event_chat_data():
    data = dict()
    data[bo.LEE] = dict()
    data[bo.LEE][bo.NAME] = 'TEST LEE'
    return data

@pytest.fixture(name='good_event_chat_data', scope='function')
def _good_event_chat_data():
    data = dict()
    data[bo.LEE] = dict()
    data[bo.LEE][bo.NAME] = 'TEST LEE'
    now_plus_10 = datetime.now() + timedelta(minutes=10)
    data[bo.LEE][bo.DATE] = now_plus_10
    data[bo.LEE][bo.LOC] = 'TEST LOC'
    data[bo.LEE][bo.MSG] = 'TEST MSG'
    return data

@pytest.fixture(name='bad_event_chat_data', scope='function')
def _bad_event_chat_data():
    data = dict()
    data[bo.LEE] = dict()
    data[bo.LEE][bo.NAME] = 'TEST LEE'
    now_minus_10 = datetime.now() - timedelta(minutes=10)
    data[bo.LEE][bo.DATE] = now_minus_10
    data[bo.LEE][bo.LOC] = 'TEST LOC'
    data[bo.LEE][bo.MSG] = 'TEST MSG'
    return data

@pytest.fixture(name='update', scope='function')
def _update(mocker):
    update = mocker.Mock()
    return update

@pytest.fixture(name='good_date_update', scope='function')
def _good_date_update(mocker, update):
    now = datetime.now()
    now_plus_10 = now + timedelta(minutes=10)
    update.message.text = now_plus_10.strftime(bo.DATE_TIME_FORMAT)
    return update

@pytest.fixture(name='bad_date_update', scope='function')
def _bad_date_update(mocker, update):
    now = datetime.now()
    now_minus_10 = now - timedelta(minutes=10)
    update.message.text = now_minus_10.strftime(bo.DATE_TIME_FORMAT)
    return update

@pytest.fixture(name='bad_format_date_update', scope='function')
def _bad_format_date_update(mocker, update):
    update.message.text = datetime.now().strftime('%f')
    return update

@pytest.fixture(name='job_queue', scope='function')
def _job_queue(mocker):
    job_queue = mocker.Mock()
    return job_queue

@pytest.fixture(name='set_event', scope='function')
def _set_event(mocker):
    return mocker.patch('bot_organizer.bot_organizer.set_event')

@pytest.fixture(name='good_one_msg_event_args', scope='function')
def _good_one_msg_event_args():
    args = []
    date_time = datetime.now() + timedelta(minutes=10)
    date = date_time.strftime(bo.DATE_FORMAT)
    args.append(date)
    time = date_time.strftime(bo.TIME_FORMAT)
    args.append(time)
    name = 'TEST EVENT'
    args.append(name)
    return args