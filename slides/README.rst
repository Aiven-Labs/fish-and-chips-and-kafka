=============================================
Slides for "Fish and Chips and Apache Kafka®"
=============================================

These are the slides for the talk
"Fish and Chips and Apache Kafka®",
which was given at `EuroPython 2023`_
on `Friday 21st July 2023`_,
presented by Tibs_

.. _`EuroPython 2023`: https://ep2023.europython.eu/
.. _`Friday 21st July 2023`: https://ep2023.europython.eu/session/fish-and-chips-and-apache-kafka
.. _Tibs: https://aiven.io/Tibs

See the `video recording on youtube`_ (and please read the corrections below the video).

.. _`video recording on youtube`: https://www.youtube.com/watch?v=T-EF8htxrsc&list=PL8uoeex94UhFcwvAfWHybD7SfNgIUBRo-&index=32

Useful links
~~~~~~~~~~~~

The Kafka libraries used in the demos:

* `aiokafka`_, which provides asynchronous access to Kafka from Python.
* `kafka-python`_, which was used for creating and managing topics.

For the terminal user interface I used in the demos, see Textual_ and Rich_.

.. _`kafka-python`: https://github.com/dpkp/kafka-python
.. _`aiokafka`: https://github.com/aio-libs/aiokafka
.. _Textual: https://github.com/Textualize/textual
.. _Rich: https://github.com/Textualize/rich

The following may also be of interest:

* `Apache Kafka® simply explained`_ on the Aiven blog, for a friendly
  explanation of the Apache Kafka fundamentals

* `Teach yourself Apache Kafka® and Python with a Jupyter notebook`_ on the
  Aiven blog. The Jupyter notebook referenced is at
  https://github.com/aiven/python-notebooks-for-apache-kafka

* `Create a JDBC sink connector`_ in the Aiven developer documentation shows
  how to setup Kafka Connect using the Aiven web console, and is thus useful
  for the "homework" on using Kafka Connect to output data to PostgreSQL.

.. _Aiven: https://aiven.io/
.. _`Apache Kafka® simply explained`: https://aiven.io/blog/kafka-simply-explained
.. _`Teach yourself Apache Kafka® and Python with a Jupyter notebook`:
   https://aiven.io/blog/teach-yourself-apache-kafka-and-python-with-a-jupyter-notebook
.. _`Create a JDBC sink connector`:
   https://docs.aiven.io/docs/products/kafka/kafka-connect/howto/jdbc-sink.html

Lastly, but definitely not least, `The Log: What every software engineer
should know about real-time data's unifying abstraction`_ is the 2013 paper by
Jay Kreps that explains the concepts behind Kafka. It is very worth a read.

.. _`The Log: What every software engineer should know about real-time data's unifying abstraction`:
   https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying

The demos
~~~~~~~~~

The source code for the demonstration programs is in the `src <../src/>`_
directory. See its `README <../src/README.md>`_ for how to run them.

The videos of the demos (which I use during the talk) are in a separate
repository, at https://github.com/tibs/fish-and-chips-and-kafka-videos (it
seems unfair to make you download them from here if you're not interested).

The slides
~~~~~~~~~~

The slides are written using reStructuredText_, and thus intended to be
readable as plain text.

The sources for the slides are in `<slides.rst>`_.

Note that github will present the ``.rst`` files in rendered form as HTML,
albeit using their own styling (which is occasionally a bit odd). If you want
to see the original reStructuredText source, you have to click on the "Raw"
link at the top of the file's page.

The PDF slides at 16x9 aspect ratio (`<slides-16x9.pdf>`_) are stored here
for convenience.

The PDF files may not always be as up-to-date as the source files, so check
their timestamps.

The QR code on the final slide was generated using the command line program
for qrencode_, which I installed with ``brew install qrencode`` on my Mac.

.. _qrencode: https://fukuchi.org/works/qrencode/

The demo videos
~~~~~~~~~~~~~~~

The videos of the demos (used during the talk) are in a separate
repository, at https://github.com/Aiven-Labs/fish-and-chips-and-kafka-videos
(it seems unfair to make you download them from here if you're not interested).


Making the PDF files
~~~~~~~~~~~~~~~~~~~~

Make a virtual environment in the traditional way::

  python3 -m venv venv

Activate it::

  source venv/bin/activate

Install the requirements using the ``requirements.txt`` file::

  pip install -r requirements.txt

Or alternatively, be explicit::

  pip install rst2pdf docutils pygments svglibq

You will also need an appropriate ``make`` program if you want to use the
Makefile.

After that, you should be able to use the Makefile to create the PDF files.
For instance::

  $ make pdf

to make them all.

For other things the Makefile can do, use::

  $ make help

.. _reStructuredText: http://docutils.sourceforge.net/rst.html

--------

Acknowledgements
~~~~~~~~~~~~~~~~

Apache,
Apache Kafka,
Kafka,
and the Kafka logo
are either registered trademarks or trademarks of the Apache Software Foundation in the United States and/or other countries

Postgres and PostgreSQL are trademarks or registered trademarks of the
PostgreSQL Community Association of Canada, and used with their permission

--------

  |cc-attr-sharealike|

  This talk and its related files are released under a `Creative Commons
  Attribution-ShareAlike 4.0 International License`_. The source code for the
  demo programs is dual-licensed as CC Attribution Share Alike and MIT.

.. |cc-attr-sharealike| image:: images/cc-attribution-sharealike-88x31.png
   :alt: CC-Attribution-ShareAlike image

.. _`Creative Commons Attribution-ShareAlike 4.0 International License`: http://creativecommons.org/licenses/by-sa/4.0/
