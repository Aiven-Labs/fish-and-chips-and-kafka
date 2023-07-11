#!/usr/bin/env python3

"""demo3_cod_and_chips_3tills_3preparers.py - A model of a very simple fish and chips shop

Now we have 3 tills, and 2 food preparers. Both the food preparers (consumers) share
a consumer group, so each message gets seen (by one consumer or the other).

Note: writes log messages to the file demo3.log.
"""

import asyncio
import json
import logging
import os
import pathlib
import random

import aiokafka
import aiokafka.helpers
import click

from ssl import SSLContext

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical

from demo_helpers import setup_topics
from demo_helpers import create_producer
from demo_helpers import OrderNumber, new_order, pretty_order
from demo_helpers import DemoWidget
from demo_helpers import PREP_FREQ_MIN, PREP_FREQ_MAX


DEMO_ID = 3
LOG_FILE = f'demo{DEMO_ID}.log'
TOPIC_NAME = f'demo{DEMO_ID}-cod-and-chips'
CONSUMER_GROUP = f'demo{DEMO_ID}-all-orders'

NUM_PRODUCERS = 3
NUM_CONSUMERS = 2


logging.basicConfig(
    format='%(asctime)s %(levelname)s %(funcName)s: %(message)s',
    level=logging.INFO,
    filename=LOG_FILE,          # log to this file
    filemode='w',               # overwrite any previous version of the file
)


# If the environment variable is set, we want to use it
KAFKA_SERVICE_URI = os.environ.get('KAFKA_SERVICE_URI')


# Synchronisation
# ===============
# 1. We don't want the consumers to miss any messages.
# 2. We also don't want the consumers to read any messages from last time the
#    demo was run.
# 3. It's non-trivial to "flush" a Kafka topic (and deleting then recreating
#    the topic takse quite a while.)
#
# So the "simplest" thing to do is to make sure that the consumers start
# listening for messages before the producers start sending them.
#
# Unfortunately, we don't have much control over how long the bit of starting
# up a producer or consumer, that comes before message handling, takes.
#
# Also, all of our code is in the `background_task` methods, which happens
# automatically when we start to visualise the widgets. And *that* means
# that the things declared first (in display order) get called first.
#
# So we can do one of two things:
#
# 1. Pull the "get ready to send/receive" code out into a separate set of
#    async operations, done before we start doing TUI stuff (which works OK,
#    in fact). But that still leaves us with the `background_task` having the
#    send/receive message loops, and thus the producers still start first.
#
# 2. Add some sort of "pause here until we're ready" lock into the
#    background task. Which is actually quite easy to do, using the
#    asyncio Barrier. So that's what I've chosen to do.
#
# Note that rater than have 2+3 as a magic constant, I've "generalised"
# the code a bit to support arbitrary numbers of producers and consumers
# - this is more flexiblity than we need, but makes things easier to
# understand and also more robust if I ever change the numbers.

# We want to wait until all all the consumers are ready.
# For simplicity, we'll instead wait until *everyone* is ready.
BARRIER = asyncio.Barrier(NUM_PRODUCERS + NUM_CONSUMERS)

async def wait_for_everyone(name):
    logging.info(f'{name} waiting for everyone')
    logging.info(f'{name} {BARRIER=}')
    index = await BARRIER.wait()
    logging.info(f'{name} believes everyone is ready')


class TillWidget(DemoWidget):

    def __init__(
            self,
            name: str,
            kafka_uri: str,
            ssl_context: SSLContext,
            topic_name: str,
            till: int,
    ) -> None:
        self.kafka_uri = kafka_uri
        self.ssl_context = ssl_context
        self.topic_name = topic_name
        self.till_number = till
        super().__init__(name)

    async def background_task(self):
        producer = await create_producer(self.kafka_uri, self.ssl_context, str(self))

        # Wait for everyone to be ready to proceed
        # If we don't, then the producers will have started sending messages
        # before the consumers are ready to read them.
        self.add_line('Waiting for everyone')
        await wait_for_everyone(f'Producer {self}')
        self.add_line('Everyone is ready')

        try:
            while True:
                await self.make_order(producer)
        except Exception as e:
            logging.error(f'Error sending message {e}')
            self.add_line(f'Error sending message {e}')
        finally:
            logging.info(f'Producer {self} stopping')
            self.add_line(f'Producer {self} stopping')
            await producer.stop()
            logging.info(f'Producer {self} stopped')

    async def make_order(self, producer):
        order = await new_order()
        order['till'] = str(self.till_number)
        order['count'] = await OrderNumber.get_next_order_number()
        self.add_line(f'Order {pretty_order(order)}')

        # Use a different partition for each till
        # Normally one would hash some part of the value to decide on a partition,
        # but it seems natural to use the till number (although we need to make
        # sure we start counting at 0)
        await producer.send(self.topic_name, value=order, partition=self.till_number - 1)


class FoodPreparerWidget(DemoWidget):

    def __init__(
            self,
            name: str,
            kafka_uri: str,
            ssl_context: SSLContext,
            topic_name: str,
    ) -> None:
        self.kafka_uri = kafka_uri
        self.ssl_context = ssl_context
        self.topic_name = topic_name
        super().__init__(name)

    async def background_task(self):

        # We don't use the create_consumer function, as we want to specify
        # a consumer group. Since we're the only demo that uses consumer
        # groups, it's not worth complicating the function to support them.

        logging.info(f'Creating consumer {self} for {self.kafka_uri}')

        try:
            consumer = aiokafka.AIOKafkaConsumer(
                self.topic_name,
                bootstrap_servers=self.kafka_uri,
                security_protocol="SSL",
                ssl_context=self.ssl_context,
                value_deserializer=lambda v: json.loads(v.decode('ascii')),
                group_id=CONSUMER_GROUP,
            )
        except Exception as e:
            logging.error(f'Error creating comsumer {self}: {e.__class__.__name__} {e}')
            return
        logging.info(f'Consumer {self} created')

        try:
            await consumer.start()
        except Exception as e:
            logging.info(f'Error starting consumer: {e.__class__.__name__} {e}')
            return
        logging.info(f'Consumer {self} started')

        # Ignore any older messages - start with the most recent
        try:
            await consumer.seek_to_end()
        except Exception as e:
            self.add_line(f'Consumer seek-to-end Exception {e.__class__.__name__} {e}')
            return

        # Wait for everyone to be ready to proceed
        # If we don't, then the producers will have started sending messages
        # before we're ready to read them.
        self.add_line('Waiting for everyone')
        await wait_for_everyone(f'Consumer {self}')
        self.add_line('Everyone is ready')

        try:
            while True:
                async for message in consumer:
                    await self.prepare_order(message.value)
        except Exception as e:
            logging.error(f'Exception receiving message {e}')
            self.add_line(f'Exception receiving message {e}')
            await consumer.stop()
        finally:
            logging.info(f'Consumer {self} stopping')
            self.add_line(f'Consumer {self} stopping')
            await consumer.stop()
            logging.info(f'Consumer {self} stopped')

    async def prepare_order(self, order):
        """Prepare an order"""
        self.add_line(f'Order {pretty_order(order)}')

        # Pretend to take some time wrapping it!
        await asyncio.sleep(random.uniform(PREP_FREQ_MIN, PREP_FREQ_MAX))

        # And now it's ready
        self.change_last_line(f'Order ready {pretty_order(order)}')


class MyGridApp(App):

    BINDINGS = [
        ("q", "quit()", "Quit"),
    ]

    def __init__(self, kafka_uri: str, ssl_context: str, topic_name: str):
        self.kafka_uri = kafka_uri
        self.ssl_context = ssl_context
        self.topic_name = topic_name
        super().__init__()

    def compose(self) -> ComposeResult:
        consumers = [
            FoodPreparerWidget(
                f'Food Preparer {index+1}',
                self.kafka_uri, self.ssl_context, self.topic_name,
            ) for index in range(NUM_CONSUMERS)
        ]

        producers = [
            TillWidget(
                f'Till {index+1}',
                self.kafka_uri, self.ssl_context, self.topic_name,
                till=index+1,
            )
            for index in range(NUM_PRODUCERS)
        ]

        with Horizontal():
            with Vertical():
                for producer in producers:
                    yield producer
            with Vertical():
                for consumer in consumers:
                    yield consumer


@click.command()
@click.option('-k', '--kafka-uri', default=KAFKA_SERVICE_URI,
              help='the URI for the Kafka service, defaulting to $KAFKA_SERVICE_URI if that is set')
@click.option('-d', '--certs-dir', default='certs',
              help='directory containing the ca.pem, service.cert and service.key files, default "certs"')
def main(kafka_uri, certs_dir):
    """A fish and chip shop demo, using Apache Kafka®
    """

    logging.info(f'Kafka URI {kafka_uri}, certs dir {certs_dir}')
    certs_path = pathlib.Path(certs_dir)

    if kafka_uri is None:
        print('The URI for the Kafka service is required')
        print('Set KAFKA_SERVICE_URI or use the -k switch')
        logging.error('The URI for the Kafka service is required')
        logging.error('Set KAFKA_SERVICE_URI or use the -k switch')
        return -1

    try:

        ssl_context = aiokafka.helpers.create_ssl_context(
            cafile=certs_path / "ca.pem",
            certfile=certs_path / "service.cert",
            keyfile=certs_path / "service.key",
        )
    except Exception as e:
        print(f'Error loading SSL certificates from {certs_path}')
        print(f'{e.__class__.__name__} {e}')
        logging.error(f'Error loading SSL certificates from {certs_path}')
        logging.error(f'{e.__class__.__name__} {e}')
        return -1

    # We will have 3 partitions, one for each till
    setup_topics(kafka_uri, ssl_context, {TOPIC_NAME: 3})

    app = MyGridApp(kafka_uri, ssl_context, TOPIC_NAME)
    app.run()

    logging.info('ALL DONE')
    print('ALL DONE')


if __name__ == '__main__':
    main()
