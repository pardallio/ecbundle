# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

import copy
import os

from .bundle import Bundle
from .logging import error, header, success,info
from .util import fullpath

__all__ = ["BundleMerger"]


class BundleMerger(object):
    def __init__(self, **kwargs):
        self.config = kwargs

    def get(self, key, default=None):
        return self.config[key] if self.config.get(key) is not None else default

    def deep_merge(self, original, updates):
        """Recursively merge `updates` into `original`.

        Rules:
        - Dictionaries are merged recursively.
        - Lists and scalar values are replaced entirely.
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
            return merged

        return copy.deepcopy(updates)

    def _load_bundle(self, path, label):
        """Load a bundle file from `path`, or return None with an error."""
        bundle_path = fullpath(path)
        if bundle_path and os.path.isfile(bundle_path):
            return Bundle(bundle_path, env=True)

        error(f"ERROR: {label} '{path}' is not a valid bundle file path")
        return None

    def _merge_named_list(self, base_bundle, key, base_items, update_items):
        """Merge a named-item list (projects/options) from update into base."""
        base_dict = {
            item.config["name"]: {k: v for k, v in item.config.items() if k != "name"}
            for item in base_items
        }
        update_dict = {
            item.config["name"]: {k: v for k, v in item.config.items() if k != "name"}
            for item in update_items
        }

        merged = self.deep_merge(base_dict, update_dict)
        base_bundle.config[key] = [{name: value} for name, value in merged.items()]

    def _apply_update(self, bundle, bundle_update):
        """Fold a single update bundle into `bundle` in place."""
        header("\nMerging bundle")
        info(f"    {bundle_update.file()}")

        self._merge_named_list(bundle, "projects",
                            bundle.projects(), bundle_update.projects())
        self._merge_named_list(bundle, "options",
                            bundle.options(), bundle_update.options())

        for key in bundle_update.config.keys():
            if key not in ("projects", "options"):
                bundle.config[key] = bundle_update.get(key)
        success(f"Bundle succesfully merged")

    def merge(self):
        bundles = self.get("bundles", [])
        if not bundles or len(bundles) < 2:
            error("ERROR: need at least one original bundle and one update bundle")
            return 1
        
        header("\nMerging bundles:")
        for bundle in bundles:
            info(f" - {bundle}")

        original_path, *update_paths = bundles


        bundle = self._load_bundle(original_path, "original bundle")
        if bundle is None:
            return 1

        for path in update_paths:
            bundle_update = self._load_bundle(path, "update bundle")
            if bundle_update is None:
                return 1
            self._apply_update(bundle, bundle_update)


        output_path = self.get("output", "merged-bundle.yml")
        
        header("\nWriting merge result into:")
        info(f" - {output_path}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(bundle.yaml())
        success(f"Bundles succesfully merged\n")
        return 0