# RestoreElasticSearchSnapshots

## Description
Manage ElasticSearch snapshots more simply - restore them from a repository, and delete the associated indexes when you're done.

## Use Case
I have an ElasticSearch instance managing my data on a daily basis, and use Curator to store that off nightly to an S3 bucket.  This script lets me pull that data back into a separate (more powerful) ElasticSearch instance for analysis later.
