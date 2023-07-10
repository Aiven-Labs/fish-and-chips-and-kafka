# Demo code for "Fish and Chips and Apache Kafka®"

<div class="contents">

</div>

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

## Future things to do

Homework projects suggested in the talk:

1.  Use a JDBC Kafka Connector to send orders from the main topic to a
    PostgreSQL® database, and then add a widget to the demo that queries
    that database periodically and updates a panel with some summary
    information (perhaps as simple as the total count of cod, chip and
    plaice orders).
2.  Use a Redis® cache to simulate the cook preparing food for the hot
    cabinet. There's a brief summary in the slides. For extra credit,
    also have the cook "wake up" periodically to check if they need to
    cook more cod or chips to keep the amount in the hot cabinet at the
    right level.

Let me know if you play with these ideas!


# Other resources

You may also be interested in

- My Aiven blog post [Get things done with the Aiven
  CLI](https://aiven.io/blog/aiven-cmdline)
- The Aiven github repository [Python Jupyter Notebooks for Apache
  Kafka®](https://github.com/aiven/python-notebooks-for-apache-kafka)
  which is a series of Jupyter Notebooks on how to start with Apache
  Kafka® and Python, using Aiven managed services.
- The [Aiven for Apache
  Kafka®](https://docs.aiven.io/docs/products/kafka.html) section of the
  [Aiven developer documentation](https://docs.aiven.io/index.html)

# Thanks

Thanks to the Stack Overflow article [Textual (Python TUI) - Enabling
long-running, external asyncio
functionality](https://stackoverflow.com/questions/71631247/textual-python-tui-enabling-long-running-external-asyncio-functionality)
for helping me understand some things when I was first writing these demo programs.


