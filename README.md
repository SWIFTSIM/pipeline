SWIFT Pipeline
==============

This repository stores the new SWIFT/EAGLE/COLIBRE pipeline. The old one is
available at [this url](https://github.com/jborrow/xl-pipeline).


Rationale
---------

We already have a pipeline; why do we need a new one? The current pipeline
suffers from a number of problems.

1. Code fragmentation: everyone has their own version of the pipeline that
   they have made small changes to, and we have no idea which version is
   being run. This can then lead to issues with interoperability, in particular
   between the pipeline outputs and the comparison script.
2. Extensibility: the current pipeline requires everything to be merged into
   one master repository, and there is only 'one copy' of these files. This
   was fine when only a single model needed to be analysed, but now that we
   have EAGLE-XL/COLIBRE/BAHAMAS all running on SWIFT, different configurations
   (and different figures!) are required.
3. Comparisons: the current method for generating comparison figures is not
   ideal. There is no webpage generated automatically, and lots of issues
   persist.

This has all occurred because at the start of the pipeline project we didn't
really know what the scope should be. Now this has become more clear, we are
ready to move to a more usable and stable code-base.


Planned Improvements
--------------------

To address the above problems, we will create a new 'pipeline' (that effectively
borrows all of the code from the old one, just with new 'stitching'). This
will aim to:

1. Have separation of code and configuration. There will be one main program,
   `swift-pipeline`, that will take your configuration as arguments to produce
   output. This differs from the current situation where the code must be
   ran from scripts within one directory.
2. Have a first-class solution for creating comparisons. The output files
   generated from `swift-pipeline` will contain all of the information required
   to entirely re-generate the figures (including ones from 'scripts' like
   the star formation history). The API for these additional plotting scripts
   will enable us to plot multiple simulation lines on one figure.

An example set of configuration files is available in `example`.


New Script API
--------------

Additional plotting scripts, such as the one used for the density-temperature
figure, now should conform to the following API and be runnable as:

```bash
python3 my_script.py \
  -s snapshot_0000.hdf5 snapshot_0001.hdf5 ... \ # These may be from different sims
  -c halo_0000.hdf5 halo_0001.hdf5 ... \  # Again different sims
  -d input_directory_one input_directory_two ... \ # Again, different sims
  -n name_one name_two name_three ... \ # Names for different sims (for legend)
  -o output_directory \
  -C config \ # Config directory containing master config.yml (for obs data and stylesheet)
```

For an example of how to implement this, please see the example in
`example/config/scripts`.


New Pipeline API
----------------

The pipeline now can be run in two modes:

1. Produce all plots and, importantly, the output line data for, a single snapshot,
   with the output line data now being stored in the input directory (i.e. next to
   the snapshot).
2. Produce all plots comparing multiple simulations (_including_ the new scripts
   through the API defined above) using the output line data.

Both of these produce webpages automatically that include all of the required data.

To run the pipeline, you now need to use a configuration file and directory.
As noted above, one of these is provided in `example`. This is passed to the pipeline,
which now acts as an executable, in the following way:

```bash
swift-pipeline -C ~/config \ # Your configuration directory (customised for sim suite)
  -c example_0000.properties \ # Name of your catalogue file
  -s snapshot_0000.hdf5 \ # Name of your snapshot file
  -i /path/to/your/snapshot \ # Path to snap directory containing properties as well
  -o ~/plots/output \ # Output directory to store HTML, etc. in.
```

This will then create `/path/to/your/snapshot/data_0000.yml`. Once you have performed
this for several simulations, you can create a comparison webpage for them using:

```bash
swift-pipeline -C ~/config \ # Your configuration directory (customised for sim suite)
  -c example_0000.properties example_0000.properties \ # Name of your catalogue files
  -s snapshot_0000.hdf5 snapshot_0000.hdf5 \ # Name of your snapshot files
  -i /path/to/your/A/snapshot /path/to/your/B/snapshot \ # Path to both directories
  -o ~/plots/output \ # Output directory to store HTML, etc. in.
```

This elevates the comparisons  to being 'first class' citizens - they are treated
in the same way as the creation of the 'real' data.


Installation
------------

To install the pipeline, you can use the python packaging manager, `pip`,

```bash
pip3 install swiftpipeline
```

This will make the `swift-pipeline` executable available.