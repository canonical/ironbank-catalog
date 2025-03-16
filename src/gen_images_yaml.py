#!/usr/bin/env python3
import csv
import yaml
import argparse
import re
from sys import stdout
from pathlib import Path


def update_yaml_with_digests(tsv_file, root="canonical"):
    data = {}

    with open(tsv_file, "r") as tsv:
        reader = csv.DictReader(tsv, delimiter="\t")
        for row in reader:
            if row["Parent"] == "None" and (digest := row["Digest"]) not in data:
                data[digest] = {"name": f"{row['Registry']}/{row['Name/Namespace']}", "os_type": "unknown", "platforms": [], "tags": []}

        tsv.seek(0)  # rewind

        for row in reader:
            if not ((key := row["Parent"]) in data or (key := row["Digest"]) in data):
                continue

            if (platform := row["Platform"]) not in (platform_list := data[key]["platforms"]) and platform != "index":
                platform_list.append(platform)

            if (platform := row["Tag"]) not in (tag_list := data[key]["tags"]):
                tag_list.append(platform)

        for digest, info in data.items():
            base = set()

            for tag in info["tags"]:
                if match := re.match(r".*(\d{2}\.\d{2}).*", tag):
                    base.update(match.groups())

            if len(base) != 1:
                raise ValueError(f"Multiple bases parsed for {info['name']}")

            major, minor = base.pop().split(".")
            info["os_type"] = f"ubuntu{major}{minor}-container"

    return {root: list(data.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update YAML file with digests from TSV file.")
    parser.add_argument("-t", dest="tsv_file", required=True, type=Path, help="Path to the TSV file containing digest information.")
    parser.add_argument("-o", dest="output_file", default=None, type=Path, help="Path to the YAML file to be updated.")
    args = parser.parse_args()

    data = update_yaml_with_digests(args.tsv_file)

    with open(args.output_file, "w") if args.output_file else stdout as fh:
        yaml.safe_dump(data, fh)
