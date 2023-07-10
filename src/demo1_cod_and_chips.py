#!/usr/bin/env python3

"""demo1_cod_and_chips.py - A model of a very simple fish and chips shop

This pulls together PoC 1 (talking to Kafka) and PoC 2 (using Textual)

Note: writes log messages to the file demo1.log.
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
from textual.widgets import Footer

from demo_helpers import setup_topics
from demo_helpers import create_producer, create_consumer
from demo_helpers import OrderNumber, new_order, pretty_order
from demo_helpers import DemoWidget
from demo_helpers import PREP_FREQ_MIN, PREP_FREQ_MAX


DEMO_ID = 3
LOG_FILE = f'demo{DEMO_ID}.log'
TOPIC_NAME = f'demo{DEMO_ID}-cod-and-chips'


logging.basicConfig(
    format='%(asctime)s %(levelname)s %(funcName)s: %(message)s',
    level=logging.INFO,
    filename=LOG_FILE,          # log to this file
    filemode='w',               # overwrite any previous version of the file
)


# If the environment variable is set, we want to use it
KAFKA_SERVICE_URI = os.environ.get('KAFKA_SERVICE_URI')


class TillWidget(DemoWidget):

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
        producer = await create_producer(self.kafka_uri, self.ssl_context, str(self))

        count = 0
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
        order['count'] = await OrderNumber.get_next_order_number()
        self.add_line(f'Order {pretty_order(order)}')
        await producer.send(self.topic_name, order)


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
        consumer = await create_consumer(self.kafka_uri, self.ssl_context, str(self), self.topic_name)

        # Ignore any older messages - start with the most recent
        try:
            await consumer.seek_to_end()
        except Exception as e:
            self.add_line(f'Consumer seek-to-end Exception {e.__class__.__name__} {e}')
            return

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
        consumer = FoodPreparerWidget('Food Preparer', self.kafka_uri, self.ssl_context, self.topic_name)
        producer = TillWidget('Till', self.kafka_uri, self.ssl_context, self.topic_name)

        with Horizontal():
            with Vertical():
                yield producer
            with Vertical():
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
        logging.error(f'Error loading SSL certificates from {certs_path}')
        logging.error(f'{e.__class__.__name__} {e}')
        return -1

    setup_topics(kafka_uri, ssl_context, {TOPIC_NAME: 1})

    app = MyGridApp(kafka_uri, ssl_context, TOPIC_NAME)
    app.run()

    logging.info('ALL DONE')



if __name__ == '__main__':
    main()
