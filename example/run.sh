#!bash

# Grab test data

wget http://virgodb.cosma.dur.ac.uk/swift-webstorage/IOExamples/cosmo_volume_example.hdf5 -O cosmo_0000.hdf5
wget http://virgodb.cosma.dur.ac.uk/swift-webstorage/IOExamples/cosmo_volume_example.properties -O cosmo_0000.properties

# Example of how to run the new pipeline.

# We log the return code after each step.
return_code=0

# With Debugging

swift-pipeline -C example/config \
               -c cosmo_0000.properties \
               -s cosmo_0000.hdf5 \
               -o test_output \
               -i . \
               -d

return_code=$(( $return_code > $? ? $return_code : $? ))

# Without debugging

swift-pipeline -C example/config \
               -c cosmo_0000.properties \
               -s cosmo_0000.hdf5 \
               -o test_output \
               -i . 
               
return_code=$(( $return_code > $? ? $return_code : $? ))

# With custom names

swift-pipeline -C example/config \
               -c cosmo_0000.properties \
               -s cosmo_0000.hdf5 \
               -o test_output \
               -i . \
               -n CustomName \
               -m metadata

return_code=$(( $return_code > $? ? $return_code : $? ))

exit $return_code