#!/usr/bin/env python3
"""
Manage snapshot restore and delete for an ElasticSearch instance

Usage: ./restoresnapshots.py --help
"""

import argparse
import fnmatch
import json
import os.path
import time
import urllib.request
import urllib.parse

import logging

logger = logging.getLogger(__name__)

MAX_CACHE_AGE = 60*60*24 # one day in seconds
SNAPSHOT_DATA_FILE = "snapshotdat.json"
PROTECTED_INDICES = [".kibana"]

def process_json(resp_json, snapshot_spec):
    """
    Select only the snapshots that match snapshot_spec
    Raise RuntimeError if there was no snapshots field in the resp_json
    """
    if "snapshots" not in resp_json:
        raise RuntimeError("Invalid server response: \n{}".format(response))

    return {snapshot["snapshot"]: snapshot
            for snapshot in resp_json["snapshots"]
            if fnmatch.fnmatch(snapshot["snapshot"], snapshot_spec)
            }

def get_snapshot_from_cache(snapshot_spec):
    """
    Try to pull snapshots from the cache
    """
    # See if the cache is too old...
    try:
        cache_age = time.time() - os.path.getmtime(SNAPSHOT_DATA_FILE)
    except FileNotFoundError as e:
        # Can't be too old if you don't exist...
        pass
    else:
        if cache_age > MAX_CACHE_AGE:
            logging.debug("Cache too old...")
            return None

    # Try to read in the cache data
    try:
        with open(SNAPSHOT_DATA_FILE, "r") as f:
            resp_json = json.load(f)
    except FileNotFoundError as e:
        logger.debug("Cache not found")
    else:
        try:
            processed = process_json(resp_json, snapshot_spec)
        except RuntimeError as e:
            logger.debug("Cache had invalid data - ignoring cache")
        else:
            return processed
    return None

def get_snapshots(url_parts, snapshot_spec = "*", force_reload = False):
    """
    Get the dict of snapshots matching spec - try the cache first,
    unless force_reload
    """
    if not force_reload:
        cache_dat = get_snapshot_from_cache(snapshot_spec)
        if cache_dat is not None:
            return cache_dat

    elastic_url = "http://{host}:{port}/_snapshot/{repository}/".format(
            host=url_parts["host"], port=url_parts["port"],
            repository=url_parts["repository"]
            )
    full_url = urllib.parse.urljoin(elastic_url, "_all")
    #full_url = urllib.parse.urljoin(elastic_url, snapshot_spec)

    # Test for URL that was constructed incorrectly, urllib can be weird
    if not full_url.startswith(elastic_url):
        raise RuntimeError("Snapshot specification built invalid Elastic URL")

    # Load from URL
    with urllib.request.urlopen(full_url) as f:
        response = f.read()

    # Turn the response from JSON into list/dict
    resp_json = json.loads(response)
    logger.debug("Server response JSON: {}".format(resp_json))

    # Save to cache
    with open(SNAPSHOT_DATA_FILE, "w") as f:
        json.dump(resp_json, f)

    return process_json(resp_json, snapshot_spec)


def restore_snapshot(url_parts, snapshot):
    """
    Restore one snapshot into the elasticsearch instance
    """
    elastic_url = "http://{host}:{port}/_snapshot/{repository}/".format(
            host=url_parts["host"], port=url_parts["port"],
            repository=url_parts["repository"]
            )
    full_url = urllib.parse.urljoin(elastic_url, snapshot) + \
            "/_restore?wait_for_completion"
    if not full_url.startswith(elastic_url):
        raise RuntimeError("Snapshot specification built invalid Elastic URL")

    req = urllib.request.Request(full_url, method="POST")
    try:
        logger.info("Sending request, will wait for completion...")
        with urllib.request.urlopen(req) as f:
            response = f.read()
            logger.info("Request complete")
    except urllib.error.HTTPError as e:
        if e.code == 500:
            logger.info("Request resulted in 500 error, "\
                    "indexes may already be restored")
        elif e.code == 503:
            logger.info("Request resulted in 503 error, "\
                    "another restore may be in progres...")
        else:
            raise e
    else:
        logger.debug("Restore request response: \n{}".format(response))

def delete_index(url_parts, index):
    """
    Delete a single index from the local elasticsearch instance
    """
    if index in PROTECTED_INDICES:
        raise RuntimeError(
                "Tried to delete protected index {}!!!".format(index))

    elastic_url = "http://{host}:{port}/".format(
            host=url_parts["host"], port=url_parts["port"]
            )
    full_url = urllib.parse.urljoin(elastic_url, index)
    if not full_url.startswith(elastic_url):
        raise RuntimeError("Snapshot specification built invalid Elastic URL")

    logging.debug("Deleting url {}".format(full_url))
    req = urllib.request.Request(full_url, method="DELETE")
    logger.info("Requesting index {} delete".format(index))
    try:
        with urllib.request.urlopen(req) as f:
            response = f.read()
            logger.info("Request complete")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.info("Index not found - skipping")

def delete_local_snapshot_data(url_parts, snapshot):
    """
    Delete the indexes for a single snapshot
    """
    snapshot_dat = get_snapshots(url_parts)

    for index in snapshot_dat[snapshot]["indices"]:
        delete_index(url_parts, index)

def main(url_parts, snapshot_spec, delete_instead = False,
        force_reload = False
        ):
    """
    Main func - display menu and dispatch to other functions...

    url_parts: a dictionary containing host, port, and repository
    snapshot_spec: specifies the snapshots, can have fnmatch-type wildcards
    delete_instead: delete indexes from snapshots, instead of restoring
    force_reload: ignore any data already in the snapshot info cache
    """
    snapshots = get_snapshots(url_parts, snapshot_spec, force_reload)

    for snapshot in snapshots:
        question_text = "{} {}? (y/n): ".format(
                "Delete" if delete_instead else "Restore",
                snapshot
                )
        answer_yn = input(question_text)
        if answer_yn in ["y", "Y"]:
            if delete_instead:
                delete_local_snapshot_data(url_parts, snapshot)
            else:
                restore_snapshot(url_parts, snapshot)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description="Simplify Restoring ElasticSearch Snapshots"
            )
    parser.add_argument("-ho", "--host", type=str, default="localhost",
            help="ElasticSearch instance's host address")
    parser.add_argument("-p", "--port", type=str, default="9200",
            help="ElasticSearch instance's TCP port")
    parser.add_argument("-r", "--repository", type=str,
            default="my_s3_repository",
            help="The ElasticSearch repository containing the snapshots"
            )
    parser.add_argument("-s", "--snapshot", type=str,
            default="*",
            help="A string specifying the snapshots to restore, "\
                    "wildcards permitted"
            )
    parser.add_argument("-d", "--delete", action="store_true",
            help="Delete the indexes corresponding with snapshots"
            )
    parser.add_argument("--reload", action="store_true",
            help="Force a reload of the cache"
            )
    parser.add_argument("--debug", action="store_true",
            help="Turn on debugging output"
            )

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    url_parts = {"host": args.host, "port": args.port,
            "repository": args.repository}

    main(url_parts, args.snapshot, args.delete, args.reload)
