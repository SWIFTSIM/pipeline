#!bash

# Example of how to run the new pipeline.

swift-pipeline --basename=eagle --catalogue=halo --snapshots=0 1 2 \
               --output=examples/plots --stylesheet=mnras.mplstyle \
               --observationaldata=observational_data_store \
               --configuration=colibre.yml