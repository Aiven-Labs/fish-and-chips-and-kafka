#!/usr/bin/env python3

"""poc1_use_kafka.py - Proof of Concept #1 - Talk to Apache Kafka® using aiokafka

This runs a simple Producer to write messages to Kafka, and a simple Consumer to
read them back.
"""

import asyncio
import json
import logging
import os
import pathlib

import aiokafka
import aiokafka.helpers
import click

from collections import deque
from datetime import datetime

from demo_helpers import setup_topics

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(funcName)s: %(message)s',
    level=logging.INFO,
)

TOPIC_NAME = 'poc1-fish-and-chips'


# If the environment variable is set, we want to use it
KAFKA_SERVICE_URI = os.environ.get('KAFKA_SERVICE_URI')


async def producer(kafka_uri, ssl_context, topic_name):

    logging.info(f'Creating producer for {kafka_uri}')
    try:
        producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=kafka_uri,
            security_protocol="SSL",
            ssl_context=ssl_context,
            value_serializer=lambda v: json.dumps(v).encode('ascii'),
        )
    except Exception as e:
        logging.error(f'Error creating producer: {e.__class__.__name__} {e}')
        return
    logging.info('Producer created')

    try:
        await producer.start()
    except Exception as e:
        logging.info(f'Error starting producer: {e.__class__.__name__} {e}')
        return
    logging.info('Producer started')

    count = 0
    while count < 10:
        await asyncio.sleep(0.5)
        count += 1
        message = { 'message': str(count), 'method': 'async' }
        logging.info(f'Sending message {message!r}')
        try:
            await producer.send(topic_name, message)
            logging.info('Message sent')
        except Exception as e:
            logging.error(f'Error sending: {e.__class__.__name__} {e}')
            logging.info('Stopping')
            await producer.stop()
            logging.info('Stopped')

    message = { 'message': 'stop', 'method': 'async' }
    logging.info(f'Sending message {message!r}')
    try:
        await producer.send(topic_name, message)
        logging.info('Message sent')
    except Exception as e:
        logging.error(f'Error sending: {e.__class__.__name__} {e}')
    finally:
        logging.info('Stopping')
        await producer.stop()
        logging.info('Stopped')


async def consumer(kafka_uri, ssl_context, topic_name):

    logging.info(f'Creating consumer for {kafka_uri}')
    try:
        consumer = aiokafka.AIOKafkaConsumer(
            topic_name,
            bootstrap_servers=kafka_uri,
            security_protocol="SSL",
            ssl_context=ssl_context,
            value_deserializer=lambda v: json.loads(v.decode('ascii')),
        )
    except Exception as e:
        logging.error(f'Error creating comsumer: {e.__class__.__name__} {e}')
        return
    logging.info('Consumer created')

    try:
        await consumer.start()
    except Exception as e:
        logging.info(f'Error starting consumer: {e.__class__.__name__} {e}')
        return
    logging.info('Started started')

    async for message in consumer:
        logging.info(f'Received {message.value}')
        if message.value['message'] == 'stop':
            break

    logging.info('Stopping')
    await consumer.stop()
    logging.info('Stopped')


async def run_tasks(kafka_uri, ssl_context, topic_name):
    """Run the various tasks asynchronously"""

    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(producer(kafka_uri, ssl_context, topic_name))
        task2 = tg.create_task(consumer(kafka_uri, ssl_context, topic_name))


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

    asyncio.run(run_tasks(kafka_uri, ssl_context, TOPIC_NAME))

    logging.info('ALL DONE')


if __name__ == '__main__':
    main()
