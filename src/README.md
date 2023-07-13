# Demo code for "Fish and Chips and Apache Kafka®"

## What we have here

Two "proof of concept" programs:

* [`poc1_use_kafka.py`](poc1_use_kafka.py) - checking we can send to and
  receive from a Kafka service
* [`poc2_textual.py`](poc2_textual.py) - showing the basics of the Textual UI
  we shall use in the demonstrations

Some support code:

* [`demo_helpers.py`](demo_helpers.py) - used in the PoCs and in the demo programs.

The demonstrations discussed in the talk:

* [`demo1_cod_and_chips.py`](demo1_cod_and_chips.py)- a till sending orders to
  a topic, and a food preparer consuming them.

* [`demo2_cod_and_chips_3tills.py`](demo2_cod_and_chips_3till.py)- three
  tills, but still only one preparer, who can't keep up.

* [`demo3_cod_and_chips_3till_2preparers.py`](demo3_cod_and_chips_3tills_2preparers.py) -
  three tills and two preparers, who can keep up.

* [`demo4_with_cook.py`](demo4_with_cook.py) - back to one till and one food
  preparer, but now we have a cook to prepare plaice for us.

## Set up

### Python version

The `poc2_textual.py` program required Python 3.11, so it can use
[`asyncio
TaskGroups`](https://docs.python.org/3/library/asyncio-task.html#task-groups)
to organise its asynchronous tasks - they're much nicer than previous ways of
doing this.

The other demo programs should work with Python 3.10.

### Install Python libraries

Make sure you're in this directory:
```shell
cd src
```

Create Python virtual environment
```shell
python -m venv venv
source venv/bin/activate
```

Install the necessary Python packages, using the `requirements.txt` file:
```shell
python -m pip install -r requirements.txt
```

Alternatively, you can install the specific requirements:
```shell
pip install textual aiokafka kafka-python click aiven-client
```

## How to run the demos with Aiven

You don't need to run the demos using Aiven services, but I think it's
the easiest option if you don't already have Kafka up and running.

### Get an account

If you don't yet have an Aiven account, you can [sign up for a free
trial](https://console.aiven.io/signup/email)

### Log in to Aiven

Get an authentication token, as described at [Create an authentication
token](https://docs.aiven.io/docs/platform/howto/create_authentication_token.html),
copy it, and log in using the following command. You'll need to replace
YOUR-EMAIL-ADDRESS with the email address you've registered with Aiven:

``` shell
avn user login YOUR-EMAIL-ADDRESS --token
```

This will prompt you to paste in your token.

### Choose a project, cloud and service plan

Aiven uses "projects" to organise which services you can access. You can
list them with:

``` shell
avn project list
```

Choose the project you want to use with the following command, replacing
`PROJECT_NAME` with the appropriate name:

``` shell
avn project switch PROJECT_NAME
```

You then need to decide what cloud you want to run the service in. Use:

``` shell
avn cloud list
```

to find the clouds. Since Aiven is based out of Helsinki, I tend to
choose `google-europe-north1`, which is Finland, but you'll want to make
your own choice.

Normally, you'd also want to decide on a service plan (which determines
the number of servers, the memory, CPU and disk resources for the
service). You can find the service plans for a cloud using:

``` shell
avn service plans --service-type kafka --cloud CLOUD_NAME
```

However, for the these demo programs a `kafka:startup-2` plan is
sufficient, and that's also the cheapest.

### Create a Kafka service

Now it's time to create the actual Kafka service, using the command
below.

The service name needs to be unique and can't be changed - I like to put
my name in it (for instance, `tibs-kafka-fish`).

It's useful to set an environment variable for the service name - so in Bash
you'd do:
```shell
export KAFKA_SERVICE_NAME=tibs-kafka-fish
```
and if you're using the [Fish shell](https://fishshell.com/) (like me) you'd do:
```shell
set -x KAFKA_SERVICE_NAME tibs-kafka-fish
```

The extra `-c` switches enable the REST API to the service (used to get
some of the information available in the web console), the ability to
create new topics by publishing to them (we definitely want this), and
use of the schema registry (which we actually don't need in this demo,
but it doesn't cost extra and is often useful).

Again, remember to replace the cloud name with the one you actually want:

``` shell
avn service create $KAFKA_SERVICE_NAME \
    --service-type kafka \
    --cloud google-europe-north1 \
    --plan startup-2 \
    -c kafka_rest=true \
    -c kafka.auto_create_topics_enable=true \
    -c schema_registry=true
```

> **Note** If you're using an existing account which has VPCs in the
> region you've chosen, then you also need to specify `--no-project-vpc`
> to guarantee that you don't use the VPC.

It takes a little while for a service to start up. You can wait for it
using:

``` shell
avn service wait $KAFKA_SERVICE_NAME
```

which will update you on the progress of the service, and exit when the
service is `RUNNING`.

### Download certificates

In order to let the demo programs talk to the Kafka service, you need to
download the appropriate certificate files. Create a directory to put
them into:

``` shell
mkdir certs
```

and then download them:

``` shell
avn service user-creds-download $KAFKA_SERVICE_NAME -d certs --username avnadmin
```

### Get the connection information

To connect to the Kafka service, you need its service URI. You can find
that out with:

``` shell
avn service get $KAFKA_SERVICE_NAME --format '{service_uri}'
```

It's useful to put that into an environment variable. With Bash, you can do:
```shell
export KAFKA_SERVICE_URI=$(avn service get $KAFKA_SERVICE_NAME --format '{service_uri}')
```

and if you're using the Fish shell (like me) that's
```shell
set -x KAFKA_SERVICE_URI (avn service get $KAFKA_SERVICE_NAME --format '{service_uri}')
```

## Exploring your service

To find out more information about a Kafka topic, look at the
documentation for [avn service
topic](https://docs.aiven.io/docs/tools/cli/service/topic.html).

You can also find useful information about a service using the [Aiven
web console](https://console.aiven.io/), on the **Services** page for
your Kafka service.

## Run a demo

*And now you're ready to run the demo programs*

In general, if you've put certificates into the `certs` directory, and set the
`KAFKA_SERVICE_URI` environment variable (and others we'll come to later),
then you can just run the demo programs with no arguments. For instance:

```shell
./demo1_cod_and_chips.py
```

You can get help with the `--help` switch.

If you want to be more explicit, you can also specify the Kafka service URI
with the `-k` switch, and the certificates directory with the `-c` switch.
For instance:

```shell
./demo1_cod_and_chips.py \
    -k tibs-kafka-fish-dev-sandbox.aivencloud.com:12693 \
    -d certs
```

or:
``` shell
./demo1_cod_and_chips.py -k $KAFKA_SERVICE_URI -d certs
```

## Log files

Each of the demo programs (the ones whose names start with `demo`) write logs
to a file called `demoN.log` - so `demo1_cod_and_chips.py` writes log messages
to `demo1.log` and so on.

The logs are useful for understanding what the program is actually doing, and
also for working out what is wrong if things fail. We use a log file because
writing the logs to the terminal would interfere with the terminal UI.

## After you're done

If you're not using your Kafka service for a while, and don't mind
losing any data in its event stream, then it makes sense to power it
off, as you don't get charged (real money or free trial credits) when a
service is powered off.

You can power off the service (remember, this will discard all your
data) with:

``` shell
avn service update $KAFKA_SERVICE --power-off
```

and bring it back again with:

``` shell
avn service update $KAFKA_SERVICE --power-on
```

This will take a little while to finish, so wait for it with:

``` shell
avn service wait KAFKA_FISH_DEMO
```

If you've entirely finished using the Kafka service, you can delete it
with:

``` shell
avn service terminate KAFKA_FISH_DEMO
```

--------

## Other things to do

Homework projects suggested in the talk:

1.  Use a Redis® cache to simulate the cook preparing food for the hot
    cabinet. There's a brief summary in the slides. For extra credit,
    also have the cook "wake up" periodically to check if they need to
    cook more cod or chips to keep the amount in the hot cabinet at the
    right level.
2.  Use a JDBC Kafka Connector to send orders from the main topic to a
    PostgreSQL® database, and then add a widget to the demo that queries
    that database periodically and updates a panel with some summary
    information (perhaps as simple as the total count of cod, chip and
    plaice orders).

Let me know if you play with these ideas!

# Use a JDBC Kafka Connector and JSON

[`demo5_json_output_to_pg.py`](demo5_json_output_to_pg.py)

This is based on
[`demo1_cod_and_chips.py`](demo1_cod_and_chips.py).

We need to make the following changes to the code:

* Add JSON schema information to our messages, since this is needed if we're
  going to use JSON messages
* Simplify the message format a bit, since the JDBC connector only supports
  basic PostgreSQL datatype
* Add a timestamp, which can be used as a unique key in the database table. We
  *could* used the `count` value, but that's going to restart from 0 each time
  we run the demo, and things would fail when we try to insert a record with
  an already existing key.

> **Note** If we were using Avro messages, we could use Karapace to "tell"
> both ends of the data process what schema was being used for messages, but
> the JSON mechanism doesn't currently support that, so we need to have an
> explicit schema in each message.

* Aiven documentation: [Create a JDBC sink connector from Apache Kafka® to
  another database](https://docs.aiven.io/docs/products/kafka/kafka-connect/howto/jdbc-sink)
  
First create the PostgreSQL database (note: a free tier database will do, or a
hobbyist plan should be plenty).

Lets set the database name as an environment variable - in Bash that's:
```shell
export PG_SERVICE_NAME tibs-pg-fish
```
and in the Fish shell:
```shell
set -x PG_SERVICE_NAME tibs-pg-fish
```

Then create the service. It's sensible to put it into the same cloud/region as
the Kafka service - although if you're using a free PostgreSQL, that may not
be possible - luckily it's not critical for a demo like this.

```shell
avn service create $PG_SERVICE_NAME \
      --service-type pg \
      --cloud google-europe-north1 \
      --plan hobbyist
```

and again wait for it to finish starting up:
```shell
avn service wait $PG_SERVICE_NAME
```

Next we need to connect to the PostgreSQL database and set up a schema. Here
I'm using the `avn` command to connect to the database, but you could equally
use `psql` or whatever other tool you prefer.

> **Note** If you go to the Connection Information page for the Aiven for
> PostgreSQL service, the **Quick Connect** button can be used to show the
> ways to connect with a variety of tools.

```shell
avn service cli $PG_SERVICE_NAME
```

```sql
CREATE TABLE demo5_cod_and_chips (
   "order_time" bigint primary key,
   "count" integer not null,
   "order" text[] not null);
```

> **Note** we [need to quote the column name `order` because it is also a
> PostgreSQL keyword](https://stackoverflow.com/questions/7651417/escaping-keyword-like-column-names-in-postgres),
> so we might as well quote all of the column names.
>
> `int64` in the JSON schema maps to `bigint` in PostgreSQL, and an array of
> strings is `text[]`.

Since we're going to use a JDBC connector with our Kafka, that means using a
service integration (between Kafka and our PostrgreSQL database), and so we
need to upgrade our Kafka to a plan that will support service integrations,
like `business-4`, and then switch Kafka Connect on so we can use them.

```shell
avn service update $KAFKA_SERVICE_NAME \
      --plan business-4 \
      -c kafka_connect=true
```

and again wait for the service to finish updating itself:
```shell
avn service wait $KAFKA_SERVICE_NAME
```

We're now going to follow the instructions at
[Create a JDBC sink connector to PostgreSQL® on a topic with a JSON schema](https://docs.aiven.io/docs/products/kafka/kafka-connect/howto/jdbc-sink#example-create-a-jdbc-sink-connector-to-postgresql-on-a-topic-with-a-json-schema)

We need the values for `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_SSL_MODE`,
`DB_USERNAME` and `DB_PASSWORD` from the Overview part of the PostgreSQL
service page, so we can create a file called `pg_sink.json`, using the
following as a template:
```json
{
    "name":"sink_fish_chips_json_schema",
    "connector.class": "io.aiven.connect.jdbc.JdbcSinkConnector",
    "topics": "demo5-cod-and-chips",
    "table.name.normalize": "true",
    "connection.url": "jdbc:postgresql://DB_HOST:DB_PORT/DB_NAME?sslmode=DB_SSL_MODE",
    "connection.user": "DB_USERNAME",
    "connection.password": "DB_PASSWORD",
    "tasks.max":"1",
    "auto.create": "false",
    "auto.evolve": "false",
    "insert.mode": "insert",
    "delete.enabled": "false",
    "pk.mode": "record_value",
    "pk.fields": "order_time",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter"
}
```
1. I've changed the connector `name` to something more appropriate.

2. The value for `topics` needs to match the topic name specified in
   [`demo5_json_output_to_pg.py`](demo5_json_output_to_pg.py) - that is,
   `demo5-cod-and-chips`.
   
3. By default, the table written to will have the same name as the topic.
   Since that includes `-` characters, we want to set `table.name.normalize`
   to `true`, which means the table name will be `demo5_cod_and_chips`

3. The value for `pk.fields` is `"order_time"`, and that together with the value
   for `pk.mode` says to use the `order_time` field from the message as its key.

4. We set `auto.create` to `false` because we have already created our target
   table, and don't need it creating for us. Similarly, we set `auto.evolve`
   to `false` because we don't want its schema to be changed for us.

5. We set `insert.mode` to `"insert"` because we should only be inserting new
   records. For PostgreSQL,
   [`upsert`](https://github.com/aiven/jdbc-connector-for-apache-kafka/blob/master/docs/sink-connector.md#upsert-mode)
   would do `INSERT .. ON CONFLICT .. DO UPDATE SET ..`, which will update a
   row if it already exists. In theory we don't want that, as each order shoud
   be unique. In practice, for a demo, this might actually be a problem, as
   restarting the demo program will restart `count` from 0 again. We'll see
   what happens in practice.

Now we should be able to create the connector:
``` shell
avn service connector create $KAFKA_SERVICE_NAME @pg_sink.json
```

> **Note** It's possible to specify the JSON at the command line, but
> generally easier to set it up correctly in a file with a text editor, and
> then use that.

To get a list of the service connectors (as a JSON structure) attached to this Kafka, use:
```shell
avn service connector list $KAFKA_SERVICE_NAME
```

To find out more about the connector, go to the Aiven console and the service
page for our Kafka, and look at the **Connectors** tab. If there are errors,
then you'll see a warning triangle symbol next to the "Tasks" value for the
connector, and clicking on that will give the Java stacktrace.

We can check the status of the connector as follows:
```shell
avn service connector status $KAFKA_SERVICE_NAME sink_fish_chips_json_schema
```

If we now run the program:
```shell
./demo5_json_output_to_pg.py
```
it will work as we expect. As normal, we can stop it by typing `q`.

If we then go back to the database, we can check the content of the table.
For instance:
```sql
select * from demo5_cod_and_chips ;
```

might give something like:
```
  order_time   | count |              order
---------------+-------+---------------------------------
 1689159326316 |     1 | {"cod & chips"}
 1689159327797 |     2 | {"cod & chips","chips & chips"}
 1689159329195 |     3 | {"cod & chips","chips & chips"}
 1689159330643 |     4 | {"cod & chips"}
 1689159332059 |     5 | {"cod & chips","chips & chips"}
 1689159333343 |     6 | {"cod & chips"}
(6 rows)
```

Note: if you want to delete the connector, then use:
```shell
avn service connector delete $KAFKA_SERVICE_NAME sink_fish_chips_json_schema
```

-----------

Discussion: is the array of strings actually a better representation of an
order than an array of arrays of strings? In a real situation, we'd have
"names" for menu items - hence `"chips & chips"` would *actually* be `"large
chips"`, and the price for `"cod & chips"` might be different than the sum of
the prices for `"cod"` and `"chips"`.

In terms of "is there plaice in this order" it doesn't make a lot of
difference - in our naive system, we're either looking for "plaice" in a list
of strings, or we're looking for "plaice" in a strings in a list. (and of
course, we're not doing it in demo5 anyway). And again, in "real life", we
might have a lookup table from "menu item" to "necessary ingredients" -
consider the traditional menu item "fish supper", which we'd probably
interpret as meaning "cod and chips".

---------

# Use a JDBC Kafka Connector, Avro and Karapace

If we don't want to pass the schema information with every message, then we
need to use a schema repository, so that both sender and receiver can use to
interpret the messages (in the exact same way).

We're going to use [`karapace`](https://www.karapace.io/) which is an open
source schema repository for Apache Kafka, and [Apache
Avro™](https://avro.apache.org/) which is a serialization format for messages.
The JDBC connector knows how to query Karapace for the schema of Avro
messages, and can thus tell how to write their data to PostgreSQL.

Aiven for Apache Kafka services have in-built support for Karapace
(you may have noticed us specifying the `schema_registry=true` option when we
created our Kafka service).


Set an environment variable to the schema registry URI:
Using bash:
```shell
export SCHEMA_REGISTRY_URI=$(avn service get tibs-kafka-fish --json | jq -r '.connection_info.schema_registry_uri')
```

Using the Fish shell:
```shell
set -x SCHEMA_REGISTRY_URI (avn service get tibs-kafka-fish --json | jq -r '.connection_info.schema_registry_uri')
```


In order to use Avro for our messages, we need to install a Python package that
understands the format. We shall use the Apache
[`avro`](https://pypi.org/project/avro/) package:

```shell
pip install avro
```

We're also going to need `httpx` (a more modern alternative to `requests`):
```shell
pip install httpx
```

[`demo6_avro_output_to_pg.py`](demo6_avro_output_to_pg.py) is a version of
[`demo5_json_output_to_pg.py`](demo5_json_output_to_pg.py) that uses Avro instead of
JSON.

1. It gains a command line option for the Karapace URI (and an equivalent
   default to the environment variable we've set)
2. It registers its Avro schema with Karapace
3. It encodes messages (before sending) using its own copy of that schema.
4. It decodes messages (after receiving) using its own copy of that schema.

Still to do: Set up the connector to write to PostgreSQL.

This time we're following the instructions at [Define a Kafka Connect
configuration
file](https://docs.aiven.io/docs/products/kafka/kafka-connect/howto/jdbc-sink#define-a-kafka-connect-configuration-file)
which assumes Avro and Karapace.

File `avro_sink.json` starts out as:
``` json
{
    "name":"sink_fish_chips_avro_karapace",
    "connector.class": "io.aiven.connect.jdbc.JdbcSinkConnector",
    "topics": "demo6-cod-and-chips",
    "table.name.normalize": "true",
    "connection.url": "DB_CONNECTION_URL",
    "connection.user": "DB_USERNAME",
    "connection.password": "DB_PASSWORD",
    "tasks.max":"1",
    "auto.create": "true",
    "auto.evolve": "false",
    "insert.mode": "insert",
    "delete.enabled": "true",
    "pk.mode": "record_key",
    "pk.fields": "order_time",
    "key.converter": "io.confluent.connect.avro.AvroConverter",
    "key.converter.schema.registry.url": "https://APACHE_KAFKA_HOST:SCHEMA_REGISTRY_PORT",
    "key.converter.basic.auth.credentials.source": "USER_INFO",
    "key.converter.schema.registry.basic.auth.user.info": "SCHEMA_REGISTRY_USER:SCHEMA_REGISTRY_PASSWORD",
    "value.converter": "io.confluent.connect.avro.AvroConverter",
    "value.converter.schema.registry.url": "https://APACHE_KAFKA_HOST:SCHEMA_REGISTRY_PORT",
    "value.converter.basic.auth.credentials.source": "USER_INFO",
    "value.converter.schema.registry.basic.auth.user.info": "SCHEMA_REGISTRY_USER:SCHEMA_REGISTRY_PASSWORD"
}
```

* We've set the `name` of the connector to indicate we're using Avro and
  Karapace
* The `topics` value names the topic for this demo, which is `demo6-cod-and-chips`
* As before, we want `table.name.normalize` to be `true`, so that the topic
  name will be converted to a legal PostgreSQL table name, `demo6_cod_and_chips`
* The database connection information ...is as before - explain it again...
* For the moment, we're leaving `auto.create` as `true`, so I don't have to
  create the PG table - I may change that later
* But there's no need for `auto.evolve` to be true, and again `insert` is all
  we need for our `insert.mode` **EDIT EDIT EDIT maybe don't assume the reader
  read the other place we said all this earlier on**
* Our key is again `order_time`


And all the upper case values come from appropriate places in the Aiven
Console, or can doubtless be found using `avn service` commands, *with the
exception of `USER_INFO`, which is meant to be left as it is*.

> **EDIT EDIT EDIT** It seems to be worth powering off my Kafka service at
> this point, and then powering it back on again, to clear any *old* (JSON)
> messages, which won't make sense to the connector. Perhaps I should instead
> find out how to tell it to "start with the latest message", rather than (as
> I assume it is doing) the earliest.

So let's create our connector:
```shell
avn service connector create $KAFKA_SERVICE_NAME @avro_sink.json
```

and run our demo program:
```shell
./demo6_avro_output_to_pg.py
```

Unfortunately the connector fails with
```
Failed to deserialize data for topic demo6-cod-and-chips to Avro
...
Caused by: org.apache.kafka.common.errors.SerializationException: Unknown magic byte!
```

so I've done something wrong.

```shell
curl -X GET $KARAPACE_REGISTRY_URI/subjects/demo6/versions/latest
```
returns the latest version of my schema, which *looks* OK
```
{"id":4,"schema":"{\"doc\":\"A fish and chip shop order\",\"fields\":[{\"name\":\"order_time\",\"type\":\"long\"},{\"name\":\"count\",\"type\":\"int\"},{\"name\":\"order\",\"type\":{\"items\":\"string\",\"type\":\"array\"}}],\"name\":\"Order\",\"type\":\"record\"}","subject":"demo6","version":5}⏎```

Here the response is as JSON:
```json
{
  "id": 4,
  "schema": "{\"doc\":\"A fish and chip shop order\",\"fields\":[{\"name\":\"order_time\",\"type\":\"long\"},{\"name\":\"count\",\"type\":\"int\"},{\"name\":\"order\",\"type\":{\"items\":\"string\",\"type\":\"array\"}}],\"name\":\"Order\",\"type\":\"record\"}",
  "subject": "demo6",
  "version": 5
}
```

Yes it has the schema defined as a string, but that seemed to be what I had to
do (and my Python code using `avro` seems to want it as a string, as well).

But hmm - I can't see anything in the `avro_sink.json` file indicating what
schema to use, so how is it meant to know? Is this another case where I'm
meant to name it after the topic?

Aha - it *is* encoded in the message. The documentation on
[Wire
format](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html#wire-format)
is presumably what I want, as I believe we're maintaining compatibility with
other libraries...

So let's try implementing that...

**Progress!** (not working, but progress)

It's now complaining that:
```
Error retrieving Avro value schema version for id 4
```
which means that it recognises that it wants the schema with id 4 - which
actually matches what I was telling it to look for.

```shell
curl -X GET $KARAPACE_REGISTRY_URI/subjects/demo6/versions/latest | jq
```
gives me back
```json
{
  "id": 4,
  "schema": "{\"doc\":\"A fish and chip shop order\",\"fields\":[{\"name\":\"order_time\",\"type\":\"long\"},{\"name\":\"count\",\"type\":\"int\"},{\"name\":\"order\",\"type\":{\"items\":\"string\",\"type\":\"array\"}}],\"name\":\"Order\",\"type\":\"record\"}",
  "subject": "demo6",
  "version": 5
}
```
so that *sounds* like the right version - so maybe I've got the connection
information in the `avro_sink.json` file wrong. Although it does *look* right.

Hmm. Further down it says:
```
Caused by: io.confluent.kafka.schemaregistry.client.rest.exceptions.RestClientException: Subject 'demo6-cod-and-chips-value' not found.; error code: 40401
```

Oh - this is a known thing (it googles quite well). I'll look at it tomorrow.

https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html#sr-schemas-subject-name-strategy

> The default naming strategy (`TopicNameStrategy``) names the schema based on the topic name 

> **Note** If you want to explore using Avro for the messages, allowing the
> schema to be specified in Karapace, rather than in each messages, see the
> [How to send and receive application data from Apache
> Kafka®](https://aiven.io/developer/how-to-send-and-receive-application-data-from-apache-kafka)
> tutorial. The
> [Prerequisites](https://aiven.io/developer/how-to-send-and-receive-application-data-from-apache-kafka#prerequisites)mention
> `kafka-python` and `confluent-kafka` instead of `aiokafka`, but their usage is similar enough that
> the examples should still be clear. For our purposes, then start from [Add
> schemas to messages with Apache
> Avro™](https://aiven.io/developer/how-to-send-and-receive-application-data-from-apache-kafka#add-schemas-to-messages-with-apache-avro-)

Next day:

Restarted Kafka.

Running demo6 doesn't seem to crash the connector, but also doesn't seem to be
creating a new database for me.

Create the table explicitly:
```sql
CREATE TABLE demo6_cod_and_chips (
   "order_time" bigint primary key,
   "count" integer not null,
   "order" text[] not null);
```
and run the demo again.

and no, still no *errors* from the connector, but also no data in the table

Oh - I changed the topic name in the program, but not in the configuration
file `avro_sink.json`. That means the connector was sitting waiting for data
in a topic that doesn't exist.

Edit the file to have:
```
"topics": "demo6_cod_and_chips",
```

and stop/restart the connector:
```shell
avn service connector delete $KAFKA_SERVICE_NAME sink_fish_chips_avro_karapace
avn service connector create $KAFKA_SERVICE_NAME @avro_sink.json
```

And now it's failing with:
```
io.confluent.kafka.schemaregistry.client.rest.exceptions.RestClientException: Subject 'demo6_cod_and_chips-value' not found.; error code: 40401
```

I can't just change the schema `name` field to `demo6_cod_and_chips-value`,
because the Python code then complains:
```
avro.errors.InvalidName: demo6_cod_and_chips-value is not a valid Avro name because it does not match the pattern (?:^|\.)[A-Za-z_][A-Za-z0-9_]*$
```
That is, as I found before, hyphens are not allowed.

Ah - re-reading https://www.karapace.io/quickstart, I think I need to change
the name used in the Karapace URI when registering the schema. So instead of
doing a POST to
```
        f'{schema_uri}/subjects/demo6/versions',
```
I maybe want to use
```
        f'{schema_uri}/subjects/demo6_cod_and_chips-value/versions',
```

And now I'm getting
```
PK mode for table 'demo6_cod_and_chips' is RECORD_KEY, but record key schema is missing
```
which I suppose makes sense - but is the schema for the key *just* the schema
for the key, or can I re-use the existing schema? And surely if it's a
different schema it will have a different id???

...**oh** - my `avro_sink.json` has `"pk.mode": "record_key"` instead of
`"pk.mode": "record_value"` - I'm telling it the wrong thing! Let's fix the
configuration and restart the connector...

and success!
```sql
defaultdb=> select * from demo6_cod_and_chips ;
  order_time   | count |              order
---------------+-------+---------------------------------
 1689238490892 |     1 | {"cod & chips"}
 1689238492138 |     2 | {"cod & chips"}
 1689238493296 |     3 | {chips}
 1689238494749 |     4 | {"cod & chips"}
 1689238495998 |     5 | {"cod & chips","chips & chips"}
 1689238497410 |     6 | {"cod & chips","chips & chips"}
 1689238498697 |     7 | {"cod & chips"}
 1689238499737 |     8 | {chips}
```

-----------

Check which of these I have discussed / should have diccussed:
``` shell
curl "$KARAPACE_REST_URI/topics"
curl $KARAPACE_REGISTRY_URI/schemas/ids/5
curl $KARAPACE_REGISTRY_URI/subjects
curl $KARAPACE_REGISTRY_URI/subjects/demo6
curl $KARAPACE_REGISTRY_URI/subjects/demo6/versions
curl $KARAPACE_REGISTRY_URI/subjects/demo6/versions/5
curl $KARAPACE_REGISTRY_URI/subjects/demo6/versions/latest
curl $KARAPACE_REGISTRY_URI/subjects/demo6/versions/latest | jq
curl $KARAPACE_REGISTRY_URI/subjects/schemas/ids/5
curl -X DELETE $KARAPACE_REGISTRY_URI/subjects/demo6



avn service cli $PG_SERVICE_NAME
avn service connector create $KAFKA_SERVICE_NAME @avro_sink.json
avn service connector create $KAFKA_SERVICE_NAME @pg_sink.json
avn service connector delete $KAFKA_SERVICE_NAME sink_fish_chips_json_schema
avn service connector delete $KAFKA_SERVICE_NAME sink_iot_json_schema
avn service connector list $KAFKA_SERVICE_NAME
avn service connector restart $KAFKA_SERVICE_NAME sink_fish_chips_json_schema
avn service connector schema $KAFKA_SERVICE_NAME io.debezium.connector.sqlserver.SqlServerConnector
avn service connector status $KAFKA_SERVICE_NAME
avn service connector status $KAFKA_SERVICE_NAME sink_fish_chips_json_schema
avn service connector status $KAFKA_SERVICE_NAME sink_io_json_schema
avn service get tibs-kafka-fish --json | jq
avn service help
avn service wait $KAFKA_SERVICE_NAME
avn user login tony.ibbs@aiven.io --token
set -x KAFKA_REST_URI (avn service get tibs-kafka-fish --json | jq -r '.connection_info.kafka_rest_uri')
set -x KAFKA_REST_URI (avn service get tibs-kafka-fish --json | jq -r '.connection_info.schema_registry_uri')
set -x SCHEMA_REGISTRY_URI (avn service get tibs-kafka-fish --json | jq -r '.connection_info.schema_registry_uri')
```

-----------

# Other resources

You may also be interested in

- The Aiven blog post [Get things done with the Aiven
  CLI](https://aiven.io/blog/aiven-cmdline)
- The Aiven github repository [Python Jupyter Notebooks for Apache
  Kafka®](https://github.com/aiven/python-notebooks-for-apache-kafka)
  which is a series of Jupyter Notebooks on how to start with Apache
  Kafka® and Python, using Aiven managed services.
- The [Aiven for Apache
  Kafka®](https://docs.aiven.io/docs/products/kafka.html) section of the
  [Aiven developer documentation](https://docs.aiven.io/index.html)
- The [Apache Kafka®](https://aiven.io/developer/kafka) section of the [Aiven
  developer center](https://aiven.io/developer) for longer articles.

# Thanks

Thanks to the Stack Overflow article [Textual (Python TUI) - Enabling
long-running, external asyncio
functionality](https://stackoverflow.com/questions/71631247/textual-python-tui-enabling-long-running-external-asyncio-functionality)
for helping me understand some things when I was first writing these demo programs.

--------

  |cc-attr-sharealike|

  This talk and its related files are released under a `Creative Commons
  Attribution-ShareAlike 4.0 International License`_. The source code for the
  demo programs is dual-licensed as CC Attribution Share Alike and MIT.

.. |cc-attr-sharealike| image:: ../src/images/cc-attribution-sharealike-88x31.png
   :alt: CC-Attribution-ShareAlike image

.. _`Creative Commons Attribution-ShareAlike 4.0 International License`: http://creativecommons.org/licenses/by-sa/4.0/
