#! /usr/bin/env python3

from typing import Optional, List, NamedTuple
from dxf import DXF
import json
import argparse
import logging
from pathlib import Path
from sys import stdout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

headers = ["Registry", "Name/Namespace", "Tag", "Platform", "Digest", "Parent"]


class RegistryInfo(NamedTuple):
    registry: str
    repo: str
    tag: str
    platform: str
    digest: str
    parent: str = "None"


def fetch_registry_info(registry: str, username: Optional[str], password: Optional[str]) -> List[RegistryInfo]:
    def get_auth(dxf, response):
        dxf.authenticate(username, password, response=response)

    logger.info(f"Connecting to registry: {registry}")
    client = DXF(registry, None, get_auth)
    table_data = [headers]

    catalog = client.list_repos()
    logger.info(f"Found {len(catalog)} repositories")

    for repo in catalog[::-1]:
        logger.info(f"Processing repository: {repo}")
        repo_client = DXF(registry, repo, get_auth)
        tags = repo_client.list_aliases()
        logger.info(f"Found {len(tags)} tags in repository {repo}")

        for tag in tags:
            digests = repo_client.get_digest(alias=tag)

            if isinstance(digests, dict):
                index_digest, response = repo_client.head_manifest_and_response(tag)
                table_data.append(RegistryInfo(registry, repo, tag, "index", index_digest))
                for platform, digest in digests.items():
                    if "unknown" in platform:
                        continue
                    table_data.append(RegistryInfo(registry, repo, tag, platform, digest, index_digest))
            else:
                config_str = ""
                for chunk in repo_client.pull_blob(digests):
                    config_str += chunk.decode("utf-8")
                config = json.loads(config_str)
                os = config.get("os", "unknown")
                arch = config.get("architecture", "unknown")
                table_data.append(RegistryInfo(registry, repo, tag, f"{os}/{arch}", digests))

    return table_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fetch a registry and collect information.")
    parser.add_argument("-r", dest="registry", help="The registry URL")
    parser.add_argument("-u", dest="username", help="Username for authentication", default=None)
    parser.add_argument("-p", dest="password", help="Password for authentication", default=None)
    parser.add_argument("-o", dest="data_path", type=Path, help="Path to data directory", default=None)

    args = parser.parse_args()
    logger.info("Starting registry fetch")
    table_data = fetch_registry_info(args.registry, args.username, args.password)
    logger.info("Registry fetch completed")

    if args.data_path:
        registry_path = args.data_path / args.registry
        registry_path.mkdir(parents=True, exist_ok=True)
        output_file = registry_path / "index.tsv"

    with open(output_file, "w") if args.data_path else stdout as fh:
        for line in table_data:
            print("\t".join(line), file=fh)
