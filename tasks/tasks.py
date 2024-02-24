# Documentation: https://docs.pyinvoke.org/en/stable/index.html

import json
import os
import re
import sys
from copy import deepcopy
from datetime import datetime
from difflib import unified_diff

import yaml
from invoke import task  # pyright: ignore[reportPrivateImportUsage]

from ._utils import date_checker, set_timer, user_confirm


@task()
def pre_autoupdate(c):
    """Autoupdate pre-commit hooks."""

    orig_mtime = os.path.getmtime("./.pre-commit-config.yaml")
    result = c.run("pre-commit autoupdate")
    if result.ok:
        new_mtime = os.path.getmtime("./.pre-commit-config.yaml")

        if orig_mtime != new_mtime:
            c.run("git add ./.pre-commit-config.yaml")
            # THE COMMAND SHOULD BE IN SINGLE QUOTES (') AND -M IN DOUBLE QUOTES (")
            # OTHERWISE QUOTES WILL BE STRIPPED
            c.run('git commit -m "[inv:task] pre-commit autoupdate"')


@task(
    help={
        "path": "Where to put the output file.",
        "no-versions": "Create output without adding package versions.",
    }
)
def conda_export(c, path="./", no_versions=False):
    """Export conda environment including installations with pip"""

    print("Exporting conda env with pip packages.")
    c_export_all_result = c.run("conda env export --json", hide="out")
    print("Exporting conda env from history.")
    c_export_from_history_result = c.run("conda env export --from-history --json", hide="out")
    print("Running pip list.")
    pip_list_result = c.run("pip list --not-required --format json", hide="out")

    if c_export_all_result.ok and c_export_from_history_result.ok and pip_list_result.ok:
        CONDA_PATTERN = r"(?P<name>^[a-z|1-9|-]+)=(?P<version>.+)=(?P<build>.+)"
        PIP_PATTERN = r"(?P<name>^[a-z|1-9|-]+)=(?P<version>.+)"
        output: dict[str, list] = {}
        no_v: dict[str, list] = {}

        pip_list = json.loads(pip_list_result.stdout)
        conda_export_all: dict = json.loads(c_export_all_result.stdout)
        conda_export_hist: dict = json.loads(c_export_from_history_result.stdout)
        del conda_export_all["prefix"]
        del conda_export_hist["prefix"]

        # building output
        output = deepcopy(conda_export_hist)
        output["dependencies"].clear()

        # selecting conda packages
        for hist_dep in conda_export_hist["dependencies"]:
            for all_dep in conda_export_all["dependencies"]:
                if isinstance(all_dep, dict) is False:
                    match = re.match(CONDA_PATTERN, all_dep)
                    if match is not None and hist_dep == match.group("name"):
                        output["dependencies"].append(all_dep)

        #  add pip version
        for dep in conda_export_all["dependencies"]:
            if isinstance(dep, dict) is False:
                match = re.match(CONDA_PATTERN, dep)
                if match is not None and match.group("name") == "pip":
                    output["dependencies"].append(dep)

        # select pip packages
        conda_pip: list = []
        out_pip: list = []

        for dep in conda_export_all["dependencies"]:
            if isinstance(dep, dict):
                conda_pip = dep["pip"]

        for pip_out in pip_list:
            for conda_out in conda_pip:
                match = re.match(PIP_PATTERN, conda_out)
                if match is not None and pip_out["name"] == match.group("name"):
                    out_pip.append(conda_out)

        # add pip
        output["dependencies"].append({"pip": out_pip})

        # sort
        custom_order = ["name", "channels", "dependencies"]
        output = {key: output[key] for key in custom_order}

        # To keep logic readable and simple
        # just strip away versions from already created dict
        if no_versions:
            no_v = deepcopy(output)
            no_v_pip: list = []
            no_v["dependencies"].clear()

            for item in output["dependencies"]:
                if isinstance(item, dict) is False:
                    match = re.match(CONDA_PATTERN, item)
                    if match is not None:
                        no_v["dependencies"].append(match.group("name"))
                if isinstance(item, dict):
                    for pip_item in item["pip"]:
                        match = re.match(PIP_PATTERN, pip_item)
                        if match is not None:
                            no_v_pip.append(match.group("name"))

            if len(no_v_pip) != 0:
                no_v["dependencies"].append({"pip": no_v_pip})

            output = no_v

        # create output file
        if not path.endswith("/"):
            path += "/"
        env_file = path + "environment.yaml"

        diff_found: bool = False
        print("\n")
        if os.path.exists(env_file):
            with open(env_file, encoding="utf-8") as existing_file:
                for idx, line in enumerate(
                    unified_diff(
                        existing_file.read().splitlines(keepends=True),
                        yaml.dump(output, sort_keys=False).splitlines(keepends=True),
                        fromfile=f"a/{env_file}",
                        tofile=f"b/{env_file}",
                        n=0,
                    )
                ):
                    if idx == 0:
                        diff_found = True
                        print("Changes found:\n")
                    print(line, end="")
        else:
            diff_found = True

        if diff_found:
            print("\nWriting to file...")
            with open(env_file, "w", newline="\n", encoding="utf-8") as out_file:
                yaml.dump(output, out_file, sort_keys=False)
            print("Success.")

            if user_confirm("\nDo you wish to commit changes?"):
                print("Starting a commit...")
                git_add = c.run(f"git add {env_file}")
                if git_add.ok:
                    print("environment.yaml successfully added to commit.")
                # THE COMMAND SHOULD BE IN SINGLE QUOTES (') AND -M IN DOUBLE QUOTES (")
                # OTHERWISE QUOTES WILL BE STRIPPED
                git_commit = c.run('git commit -m "[inv:task] environment update"')
                if git_commit.ok:
                    print("environment.yaml successfully committed.")
            else:
                print("Exiting.")
        else:
            print("Nothing to export. Exiting.")


@task(
    help={
        "delay": "Delay before start updates check.",
        "period": "How often check for updates. In days.",
    }
)
def updates_check(c, period=0, delay=0):
    """Updates checker."""

    FILE_DIR = "./.tmp/last-update-check"

    set_timer(delay)
    check_for_updates = date_checker(FILE_DIR, period)
    if check_for_updates[0]:
        with open(FILE_DIR, "w", encoding="utf-8") as out_file:
            out_file.write(datetime.now().isoformat())
        print("Checking for updates...")
        c.run("pre-commit autoupdate")
        c.run("conda update --all")
        print("Done!")
        sys.exit(0)
    else:
        print(f"Last check is fresh enough. \nLast checked: {check_for_updates[1]}")
