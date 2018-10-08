# RestoreElasticSearchSnapshots

## Description
Manage ElasticSearch snapshots more simply - restore them from a repository, and delete the associated indexes when you're done.

## Use Case
I have an ElasticSearch instance managing my data on a daily basis, and use Curator to store that off nightly to an S3 bucket.  This script lets me pull that data back into a separate (more powerful) ElasticSearch instance for analysis later.


## Usage
restoresnapshots.py --help

"""
usage: restoresnapshots.py [-h] [-ho HOST] [-p PORT] [-r REPOSITORY]
                           [-s SNAPSHOT] [-d] [--reload] [--debug]

Simplify Restoring ElasticSearch Snapshots

optional arguments:
  -h, --help            show this help message and exit
  -ho HOST, --host HOST
                        ElasticSearch instance's host address
  -p PORT, --port PORT  ElasticSearch instance's TCP port
  -r REPOSITORY, --repository REPOSITORY
                        The ElasticSearch repository containing the snapshots
  -s SNAPSHOT, --snapshot SNAPSHOT
                        A string specifying the snapshots to restore,
                        wildcards permitted
  -d, --delete          Delete the indexes corresponding with snapshots
  --reload              Force a reload of the cache
  --debug               Turn on debugging output
"""
