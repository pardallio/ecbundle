# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

import copy
import os
from collections import OrderedDict

from .bundle import Bundle
from .logging import error, header, success
from .util import fullpath, mkdir_p, symlink_force

__all__ = ["BundleMerger"]


class BundleMerger(object):
    def __init__(self, **kwargs):
        self.config = kwargs

    def get(self, key, default=None):
        return self.config[key] if self.config[key] is not None else default

    def deep_merge(self, original, updates):
        """Recursively merge `updates` into `original`.

        Rules:
        - Dictionaries and  are merged recursively.
        - lists and scalar values are replaced entirely.
        - Keys missing from `updates` remain unchanged.
        """
        if isinstance(original, dict) and isinstance(updates, dict):
            merged = copy.deepcopy(original)
            for key, value in updates.items():
                if key in merged:
                    if isinstance(merged[key], dict) and isinstance(value, dict):
                        merged[key] = self.deep_merge(merged[key], value)
                    else:
                        merged[key] = copy.deepcopy(value)

                else:
                    merged[key] = copy.deepcopy(value)

        else:
            return copy.deepcopy(updates)

        return merged

    def bundle(self, update=False):
        arg = "bundle"
        if update:
            arg += "_update"
        bundle_path = fullpath(self.get(arg, None))
        if bundle_path:
            if os.path.isfile(bundle_path):
                return Bundle(bundle_path, env=True)
            if not os.path.isdir(bundle_path):
                error(f"ERROR: --{arg} argument is not a valid bundle file path")
                return None

        return None

    def merge(self):
        bundle = self.bundle()
        bundle_update = self.bundle(update=True)
        if not (bundle and bundle_update):
            return 1

        success("\nMerging bundle  ")
        header(f"    {bundle_update.file()} into {bundle.file()}")

        # merging projects
        project_dict = {
            item.config["name"]: {k: v for k, v in item.config.items() if k != "name"}
            for item in bundle.projects()
        }

        updated_project_dict = {
            item.config["name"]: {k: v for k, v in item.config.items() if k != "name"}
            for item in bundle_update.projects()
        }

        updated_dict = self.deep_merge(project_dict, updated_project_dict)

        bundle.config["projects"] = [
            {key: value} for key, value in updated_dict.items()
        ]

        # merging options
        option_dict = {
            item.config["name"]: {k: v for k, v in item.config.items() if k != "name"}
            for item in bundle.options()
        }

        updated_option_dict = {
            item.config["name"]: {k: v for k, v in item.config.items() if k != "name"}
            for item in bundle_update.options()
        }

        updated_dict = self.deep_merge(option_dict, updated_option_dict)

        bundle.config["options"] = [{key: value} for key, value in updated_dict.items()]

        # merge remaining keys

        for key in bundle_update.config.keys():
            if key not in ["projects", "options"]:
                bundle.config[key] = bundle_update.get(key)

        with open(self.get("o", None), "w", encoding="utf-8") as f:
            f.write(bundle.yaml())

        return 0
