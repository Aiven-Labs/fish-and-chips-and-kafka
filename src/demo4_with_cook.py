#!/usr/bin/env python3

"""demo4_with_cook.py - A model of a very simple fish and chips shop

One till, one food preparer, and a very simple model of a cook for plaice

Note: writes log messages to the file demo4.log.
"""

import asyncio
import itertools
import json
import logging
import os
import pathlib
import random

import aiokafka.helpers
import click

from ssl import SSLContext

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical

from demo_helpers import setup_topics
from demo_helpers import create_producer, create_consumer
from demo_helpers import OrderNumber, new_order, pretty_order
from demo_helpers import DemoWidget
from demo_helpers import PREP_FREQ_MIN, PREP_FREQ_MAX
from demo_helpers import COOK_FREQ_MIN, COOK_FREQ_MAX


DEMO_ID = 4
LOG_FILE = f'demo{DEMO_ID}.log'
TOPIC_ORDERS = f'demo{DEMO_ID}-orders'
TOPIC_COOK = f'demo{DEMO_ID}-cook'


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
            orders_topic: str,
    ) -> None:
        self.kafka_uri = kafka_uri
        self.ssl_context = ssl_context
        self.orders_topic = orders_topic
        super().__init__(name)

    async def background_task(self):
        producer = await create_producer(self.kafka_uri, self.ssl_context, str(self))

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
        order = await new_order(allow_plaice=True)
        order['count'] = await OrderNumber.get_next_order_number()
        order['till'] = '1'  # we only have one till
        self.add_line(f'Order {pretty_order(order)}')
        await producer.send(self.orders_topic, order)


class FoodPreparerWidget(DemoWidget):

    def __init__(
            self,
            name: str,
            kafka_uri: str,
            ssl_context: SSLContext,
            orders_topic: str,
            cook_topic: str,
    ) -> None:
        self.kafka_uri = kafka_uri
        self.ssl_context = ssl_context
        self.orders_topic = orders_topic
        self.cook_topic = cook_topic
        super().__init__(name)

    async def background_task(self):
        consumer = await create_consumer(self.kafka_uri, self.ssl_context, str(self), self.orders_topic)

        # Ignore any older messages - start with the most recent
        try:
            await consumer.seek_to_end()
        except Exception as e:
            self.add_line(f'Consumer seek-to-end Exception {e.__class__.__name__} {e}')
            return

        # A producer to send messages to the cook
        self.producer = await create_producer(self.kafka_uri, self.ssl_context, str(self))

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


    def all_order_available(self, order):
        """Work out if all of the order can be prepared immediately

        Note: alters the order
        """
        # If the order isn't marked "ready or not", look to see if it
        # contains plaice. If it does, it needs that plaice to be cooked
        if 'ready' not in order:
            all_items = itertools.chain(*order['order'])
            order['ready'] = 'plaice' not in all_items

        return order['ready']

    async def prepare_order(self, order):
        """Prepare an order"""
        order_available = self.all_order_available(order)
        self.add_line(f'Order {pretty_order(order)}')

        if order_available:
            await asyncio.sleep(random.uniform(PREP_FREQ_MIN, PREP_FREQ_MAX))

            self.change_last_line(f'Order ready {pretty_order(order)}')
        else:
            await self.producer.send(self.cook_topic, order)
            self.change_last_line(f'COOK  {pretty_order(order)}')


class CookWidget(DemoWidget):

    def __init__(
            self,
            name: str,
            kafka_uri: str,
            ssl_context: SSLContext,
            orders_topic: str,
            cook_topic: str,
    ) -> None:
        self.kafka_uri = kafka_uri
        self.ssl_context = ssl_context
        self.orders_topic = orders_topic
        self.cook_topic = cook_topic
        super().__init__(name)

    async def background_task(self):
        # A consumer to receive messages sent to the cook topic
        consumer = await create_consumer(self.kafka_uri, self.ssl_context, str(self), self.cook_topic)

        # Ignore any older messages - start with the most recent
        try:
            await consumer.seek_to_end()
        except Exception as e:
            self.add_line(f'Consumer seek-to-end Exception {e.__class__.__name__} {e}')
            return

        # A producer to send messages back to the food preparer
        self.producer = await create_producer(self.kafka_uri, self.ssl_context, str(self))

        try:
            while True:
                async for message in consumer:
                    await self.cook_order(message.value)
        except Exception as e:
            logging.error(f'Exception receiving message {e}')
            self.add_line(f'Exception receiving message {e}')
            await consumer.stop()
        finally:
            logging.info(f'Consumer {self} stopping')
            self.add_line(f'Consumer {self} stopping')
            await consumer.stop()
            logging.info(f'Consumer {self} stopped')

    async def cook_order(self, order):
        """Cook (the plaice in) an order"""
        self.add_line(f'Cooking {pretty_order(order)}')

        # "Cook" the (plaice in the) order
        await asyncio.sleep(random.uniform(COOK_FREQ_MIN, COOK_FREQ_MAX))

        # It's important to remember to mark the order as ready now!
        # (forgetting to do that means the order will keep going round the loop)
        order['ready'] = True

        self.change_last_line(f'Cooked {pretty_order(order)}')

        await self.producer.send(self.orders_topic, order)
        self.add_line(f'Order {order["count"]} available')


class MyGridApp(App):

    BINDINGS = [
        ("q", "quit()", "Quit"),
    ]

    def __init__(self, kafka_uri: str, ssl_context: str, orders_topic: str, cook_topic: str):
        self.kafka_uri = kafka_uri
        self.ssl_context = ssl_context
        self.orders_topic = orders_topic
        self.cook_topic = cook_topic
        super().__init__()

    def compose(self) -> ComposeResult:
        producer = TillWidget(
            'Till', self.kafka_uri, self.ssl_context, self.orders_topic,
        )
        consumer = FoodPreparerWidget(
            'Food Preparer', self.kafka_uri, self.ssl_context, self.orders_topic, self.cook_topic,
        )
        cook = CookWidget(
            'Cook', self.kafka_uri, self.ssl_context, self.orders_topic, self.cook_topic,
        )

        with Horizontal():
            with Vertical():
                yield producer
            with Vertical():
                yield consumer
            with Vertical():
                yield cook


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

    setup_topics(kafka_uri, ssl_context, {TOPIC_ORDERS: 1, TOPIC_COOK: 1})

    app = MyGridApp(kafka_uri, ssl_context, TOPIC_ORDERS, TOPIC_COOK)
    app.run()

    logging.info('ALL DONE')
    print('ALL DONE')


if __name__ == '__main__':
    main()
