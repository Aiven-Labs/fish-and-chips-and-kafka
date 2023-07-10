#!/usr/bin/env python3

"""Helpers and common code for the demo programs.
"""

import asyncio
import json
import logging
import random
import time

from collections import deque
from ssl import SSLContext

import aiokafka

# We need kafka-python for admin tasks
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

from rich.panel import Panel
from textual.app import RenderResult
from textual.widgets import Static


# Bounds on how often a new order occurs
ORDER_FREQ_MIN = 1.0
ORDER_FREQ_MAX = 1.5

# Bounds on how long it takes to prepare an order
PREP_FREQ_MIN = 0.5
PREP_FREQ_MAX = 1.0

# Bounds on how long it takes to cook an order
COOK_FREQ_MIN = 3.0
COOK_FREQ_MAX = 3.2


def setup_topics(kafka_uri, ssl_context, topic_dict):
    """Make sure that the topi we want exists, with the correct number of
    partitions.

    Also makes sure that we won't see any old events.

    `topic_dict` is a dictionary of `topic_name`: `num_partitions`
    """

    # For this we still need to use the more traditional kafka-python library
    admin = KafkaAdminClient(
        bootstrap_servers=kafka_uri,
        security_protocol="SSL",
        ssl_context=ssl_context,
    )

    logging.info(f'Making sure topics {", ".join(topic_dict.keys())} now exist')
    topics = [
        NewTopic(name=name, num_partitions=num_partitions, replication_factor=1)
        for name, num_partitions in topic_dict.items()
    ]
    try:
        admin.create_topics(topics)
    except TopicAlreadyExistsError:
        # If the topics already exist, good
        pass

    count = 0
    while count < 10:
        topics = admin.list_topics()
        logging.info(f'Topics: {topics}')
        names = set(topic_dict.keys())
        if names.issubset(topics):  # All our topic names are present
            return
        count += 1
        time.sleep(1)


class OrderNumber:
    """An order number that we can increment safely from different async tasks
    """

    lock = asyncio.Lock()
    count = 0

    @classmethod
    async def get_next_order_number(cls):
        async with cls.lock:
            cls.count += 1
            return cls.count


async def new_order(allow_plaice=False):
    """Wait a random time, return a random order.

    Note that it doesn't include the order number, because that can only be
    set by the TILL receiving the order.
    """

    # Wait somewhere between 0.5 and 1 seconds (these are fast customers!)
    await asyncio.sleep(random.uniform(ORDER_FREQ_MIN, ORDER_FREQ_MAX))

    die_roll = random.randrange(6) + 1  # die have 1-6 dots :)
    if die_roll == 6 and allow_plaice:
        order = {
            'order': [
                ['cod', 'chips'],
                ['plaice', 'chips'],
            ]
        }
    elif die_roll == 5:
        order = {
            'order': [
                ['cod', 'chips'],
                ['chips', 'chips'],
            ]
        }
    elif die_roll == 4:
        order = {
            'order': [
                ['chips'],
            ]
        }
    else:
        order = {
            'order': [
                ['cod', 'chips'],
            ]
        }
    return order


def pretty_order(order):
    """Provide a pretty representation of an order's 'order' data.
    """

    # We assume that ['chips', 'chips'] is our way of saying "a large portion
    # of chips". We also assume that ['chips', 'chips', 'chips'] is not a thing,
    # nor is ['cod', 'cod'], and doubtless other oddities.
    parts = []

    if 'count' in order:
        parts.append(f'{order["count"]}:')

    if 'ready' in order and order['ready']:
        parts.append('✓')

    food = []
    for item in order['order']:
        if len(item) == 2 and item[0] == item[1] == 'chips':
            food.append(f'large chips')
        else:
            food.append(' and '.join(item))
    parts.append(', '.join(food))

    return ' '.join(parts)


class DemoWidget(Static):
    """Provide common functionality for our demo widgets

    Subclass, and then make multiple instances of the subclass, which will
    share the same `lines` dictionary.

    This very simple usage subclasses Static and redraws the entire panel
    every time we make an alteration.

    Don't forget to re-implement background_task
    """

    # Maximum number of lines to keep for a widget display
    MAX_LINES = 40

    DEFAULT_CSS = """
    DemoWidget {
        background: #f6fde3;
        height: 1fr;
        color: black;
    }

    .column {
        width: 1fr;
    }
    """

    def __init__(self, name: str) -> None:
        self.lines = deque(maxlen=self.MAX_LINES)

        super().__init__(name=name)

        self.redraw()

    def __str__(self):
        return self.name

    def redraw(self):
        self.update(self.make_panel())

    def make_text(self, width, height):
        # "magic value" of 2 is the number of characters taken to draw the
        # border to our Panel.
        #
        # We don't want our lines to wrap, so we truncate them, and since
        # we have left and right borders, that means 2x2
        lines = [line[:width-4] for line in self.lines]
        # We only want to display as many lines as we have room for, so
        # we need to truncate the lines, remembering to allow for the
        # the bottom panel border
        return '\n'.join(lines[-(height-2):])

    def make_panel(self) -> RenderResult:
        text = self.make_text(self.size.width, self.size.height)
        return Panel(text, title=self.name)

    def add_line(self, text):
        """Add a line of text to our scrolling display"""
        self.lines.append(text)
        self.redraw()

    def change_last_line(self, text):
        """Change the last line of text to our scrolling display"""
        self.lines[-1] = text
        self.redraw()

    async def background_task(self):
        while True:
            self.add_line('Implement a real background task')
            await asyncio.sleep(1)

    async def on_mount(self):
        asyncio.create_task(self.background_task())


async def create_producer(
        kafka_uri:str,
        ssl_context: SSLContext,
        name: str,
) -> aiokafka.AIOKafkaProducer:
    """Create a new Producer, and wait for it to start.
    """
    logging.info(f'Creating producer {name} for {kafka_uri}')
    try:
        producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=kafka_uri,
            security_protocol="SSL",
            ssl_context=ssl_context,
            value_serializer=lambda v: json.dumps(v).encode('ascii'),
        )
    except Exception as e:
        logging.error(f'Error creating producer {name}: {e.__class__.__name__} {e}')
        return
    logging.info(f'Producer {name} created')

    try:
        await producer.start()
    except Exception as e:
        logging.info(f'Error starting producer {name}: {e.__class__.__name__} {e}')
        return
    logging.info(f'Producer {name} started')
    return producer


async def create_consumer(
        kafka_uri:str,
        ssl_context: SSLContext,
        name: str,
        topic_name: str,
) -> aiokafka.AIOKafkaConsumer:
    """Create a new Consumer, and wait for it to start.
    """
    logging.info(f'Creating consumer {name} for {kafka_uri}')
    try:
        consumer = aiokafka.AIOKafkaConsumer(
            topic_name,
            bootstrap_servers=kafka_uri,
            security_protocol="SSL",
            ssl_context=ssl_context,
            value_deserializer=lambda v: json.loads(v.decode('ascii')),
        )
    except Exception as e:
        logging.error(f'Error creating comsumer {name}: {e.__class__.__name__} {e}')
        return
    logging.info(f'Consumer {name} created')

    try:
        await consumer.start()
    except Exception as e:
        logging.info(f'Error starting consumer: {e.__class__.__name__} {e}')
        return
    logging.info(f'Consumer {name} started')
    return consumer
