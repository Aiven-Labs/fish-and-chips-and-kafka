#!/usr/bin/env python3

"""demo6_avro_output_to_pg.py - A model of a very simple fish and chips shop

One till, one food preparer, and output to PostgreSQL via a JDBC sink
connector. That last mostly happens outside our concern.

This version uses Avro to encode messaages, rather than JSON, and
Karapace as a schema registry.

Note: writes log messages to the file demo6.log.
"""

import asyncio
import datetime
import io
import json
import logging
import os
import pathlib
import random
import struct

import aiokafka
import aiokafka.helpers
import click
import avro
import avro.io
import avro.schema
import httpx

from ssl import SSLContext

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical

from demo_helpers import setup_topics
from demo_helpers import create_producer, create_consumer
from demo_helpers import OrderNumber, new_order, pretty_order
from demo_helpers import DemoWidget
from demo_helpers import PREP_FREQ_MIN, PREP_FREQ_MAX


DEMO_ID = 6
LOG_FILE = f'demo{DEMO_ID}.log'

# Use underlines so that the topic name will also work as an Avro schema name
# (the JDBC connector wants the names to match, at least by default)
TOPIC_NAME = f'demo{DEMO_ID}_cod_and_chips'


logging.basicConfig(
    format='%(asctime)s %(levelname)s %(funcName)s: %(message)s',
    level=logging.INFO,
    filename=LOG_FILE,          # log to this file
    filemode='w',               # overwrite any previous version of the file
)


# If environment variables are set, we want to use them
KAFKA_SERVICE_URI = os.environ.get('KAFKA_SERVICE_URI')
SCHEMA_REGISTRY_URI = os.environ.get('SCHEMA_REGISTRY_URI')


# We're going to keep the same message format as in demo5, so we can produce
# equivalent tables in PostgreSQL
AVRO_SCHEMA = {
    'doc': 'A fish and chip shop order',
    'name': TOPIC_NAME,
    'type': 'record',
    'fields': [
        {'name': 'order_time', 'type': 'long'},
        {'name': 'count', 'type': 'int'},
        # An array type is a *nested* type. It took me the longest time
        # to figure this out! Eventually I found
        # https://stackoverflow.com/questions/54093898/how-to-create-object-that-contains-array-of-string-in-avro-schema
        {'name': 'order', 'type': {
            'type': 'array', 'items': 'string'},
         }
    ],
}


# When we're passing the Avro schema around, we need to pass it as a string
AVRO_SCHEMA_AS_STR = json.dumps(AVRO_SCHEMA)


# Parsing the schema both validates it, and also puts it into a form that
# can be used when envoding/decoding message data
PARSED_SCHEMA = avro.schema.parse(AVRO_SCHEMA_AS_STR)


def register_schema(schema_uri):
    """Register our schema with Karapace.

    Returns the schema id, which gets embedded into the messages.
    """
    r = httpx.post(
        f'{schema_uri}/subjects/{TOPIC_NAME}-value/versions',
        json={"schema": AVRO_SCHEMA_AS_STR}
    )
    logging.info(f'Registered schema {r} {r.text=} {r.json()=}')
    response_json = r.json()
    return response_json['id']


def pretty_order(order):
    """We redefine this function to cope with the "flattened" order parts
    """
    parts = []
    if 'count' in order:
        parts.append(f'{order["count"]}:')
    if 'ready' in order and order['ready']:
        parts.append('✓')
    food = []
    for item in order['order']:
        if item == 'chips & chips':
            food.append(f'large chips')
        else:
            food.append(item)
    parts.append(', '.join(food))
    return ' '.join(parts)


def timestamp():
    """Unix timestamp in milliseconds"""
    now = datetime.datetime.now(datetime.timezone.utc)
    return int(now.timestamp() * 1000)


class TillWidget(DemoWidget):

    def __init__(
            self,
            name: str,
            kafka_uri: str,
            ssl_context: SSLContext,
            topic_name: str,
            schema_id: int,
    ) -> None:
        self.kafka_uri = kafka_uri
        self.ssl_context = ssl_context
        self.topic_name = topic_name
        self.schema_id = schema_id
        super().__init__(name)

    async def background_task(self):
        producer = await create_producer(
            self.kafka_uri, self.ssl_context, str(self), as_json=False,
        )

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
        # Flatten the individual parts of the order
        order['order'] = [' & '.join(x) for x in order['order']]
        # Add a timestamp
        order['order_time'] = timestamp()

        # The Avro encoder works by writing to a "file like" object,
        # so we shall use a BytesIO instance.
        writer = avro.io.DatumWriter(PARSED_SCHEMA)
        byte_data = io.BytesIO()

        # According to
        # https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html#wire-format
        # (Confluent Developer > Platform > Schema Management > Fundamentals > Schema Formats > Wire format)
        # the Confluent JDBC Connector needs us to put the schema id on the front of
        # each Avro message. We need to prepend a 0 byte and then the schema
        # id as a 4 byte value.
        # We'll just do this by hand using the Python `struct` library.
        header = struct.pack('>bI', 0, self.schema_id)
        byte_data.write(header)

        # And then we add the actual data
        encoder = avro.io.BinaryEncoder(byte_data)
        writer.write(order, encoder)
        raw_bytes = byte_data.getvalue()

        self.add_line(f'Order {pretty_order(order)}')
        await producer.send(self.topic_name, raw_bytes)


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
        consumer = await create_consumer(
            self.kafka_uri, self.ssl_context, str(self), self.topic_name, as_json=False,
        )

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

    async def prepare_order(self, raw_bytes):
        """Prepare an order"""
        # We need to ignore the first 5 bytes, as they're the 0 byte
        # plus schema id.
        # (Since we already know the schema, and since it's this program
        # that wrote the messages, there's no point to checking if the
        # schema id is the same as we expect, or in trying to actually
        # look up the schema from the registry.)
        #
        # Again, we need to read from a "file like" object, which
        # BytesIO lets us do.
        byte_data = io.BytesIO(raw_bytes[5:])

        decoder = avro.io.BinaryDecoder(byte_data)
        reader = avro.io.DatumReader(PARSED_SCHEMA)
        order = reader.read(decoder)

        self.add_line(f'Order {pretty_order(order)}')

        # Pretend to take some time wrapping up the fish and chips!
        await asyncio.sleep(random.uniform(PREP_FREQ_MIN, PREP_FREQ_MAX))

        # And now it's ready
        self.change_last_line(f'Order ready {pretty_order(order)}')


class MyGridApp(App):

    BINDINGS = [
        ("q", "quit()", "Quit"),
    ]

    def __init__(self, kafka_uri: str, ssl_context: str, topic_name: str, schema_id: int):
        self.kafka_uri = kafka_uri
        self.ssl_context = ssl_context
        self.topic_name = topic_name
        self.schema_id = schema_id
        super().__init__()

    def compose(self) -> ComposeResult:
        consumer = FoodPreparerWidget(
            'Food Preparer', self.kafka_uri, self.ssl_context, self.topic_name,
        )
        producer = TillWidget(
            'Till', self.kafka_uri, self.ssl_context, self.topic_name, self.schema_id,
        )

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
@click.option('-s', '--schema-uri', default=SCHEMA_REGISTRY_URI,
              help='the URI for the Karapace schema registry, defaulting to $SCHEMA_REGISTRY_URI if that is set')
def main(kafka_uri, certs_dir, schema_uri):
    """A fish and chip shop demo, using Apache Kafka®
    """

    logging.info(f'Kafka URI {kafka_uri}, certs dir {certs_dir}, schema URI {schema_uri}')
    certs_path = pathlib.Path(certs_dir)

    if kafka_uri is None:
        print('The URI for the Kafka service is required')
        print('Set KAFKA_SERVICE_URI or use the -k switch')
        logging.error('The URI for the Kafka service is required')
        logging.error('Set KAFKA_SERVICE_URI or use the -k switch')
        return -1

    if schema_uri is None:
        print('The URI for the Karapace schema registry is required')
        print('Set SCHEMA_REGISTRY_URI or use the -s switch')
        logging.error('The URI for the Karapace schema registry is required')
        logging.error('Set SCHEMA_REGISTRY_URI or use the -s switch')
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

    try:
        schema_id = register_schema(schema_uri)
    except Exception as e:
        print(f'Error registering schema at {schema_uri}')
        print(f'{e.__class__.__name__} {e}')
        logging.error(f'Error registering schema at {schema_uri}')
        logging.error(f'{e.__class__.__name__} {e}')
        return -1

    setup_topics(kafka_uri, ssl_context, {TOPIC_NAME: 1})

    app = MyGridApp(kafka_uri, ssl_context, TOPIC_NAME, schema_id)
    app.run()

    logging.info('ALL DONE')


if __name__ == '__main__':
    main()
