import os
import re
import json
import subprocess
import sys


def run_or_empty(cmd: list) -> list:
    """Ejecuta cmd y devuelve salida; si falla, devuelve lista vacía."""
    try:
        out = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, text=True)
        return out.stdout.splitlines()
    except subprocess.CalledProcessError:
        return []


def run(base_sha: str, head_sha: str, validate: bool):
    all_changed_list = run_or_empty(
        ["git", "diff", "--name-only", "--diff-filter=AM", base_sha, head_sha]
    )
    all_changed = "\n".join(all_changed_list)
    print(f"=> all_changed: {all_changed}")

    pattern_relevant = re.compile(r'^(config/|dataset/|pipeline/|linkedService/|trigger/|src/)')
    relevant_list = [f for f in all_changed_list if pattern_relevant.match(f)]
    relevant = "\n".join(relevant_list)
    print(f"=> relevant: {relevant}")

    config_subfolders = sorted({
        f.split("/", 2)[1]
        for f in relevant_list
        if f.startswith("config/") and len(f.split("/", 2)) > 1
    })
    config_subfolders_str = "\n".join(config_subfolders)
    print(f"=> config_subfolders: {config_subfolders_str}")

    count_config = len([x for x in config_subfolders if x != ""])
    print(f"count_config: {count_config}")

    pattern_other = re.compile(r"^(dataset|pipeline|linkedService|trigger|src)/")
    other_list = [f for f in relevant_list if pattern_other.match(f)]
    other = "\n".join(other_list)
    print(f"=> other: {other}")

    # Determine the value of the deploy flag and use_cases
    deploy = False
    has_errors = False
    if count_config > 1:
        print("Case 0: multiple config subfolders")
        has_errors = True
        use_cases = config_subfolders
        deploy = False
    elif count_config == 1 and len(other_list) == 0:
        print("Case 1: config subfolder with no other changes")
        single = config_subfolders[0]
        use_cases = [single]
        deploy = True
    elif count_config == 0 and len(other_list) > 0:
        print("Case 2: no config subfolder but other changes")
        try:
            all_subfolders = [
                name for name in os.listdir("config")
                if os.path.isdir(os.path.join("config", name))
            ]
        except FileNotFoundError:
            all_subfolders = []
        use_cases = all_subfolders
        deploy = True
    elif count_config > 0 and len(other_list) > 0:
        print("Case 3: config subfolder with other changes")
        has_errors = True
        use_cases = config_subfolders
        deploy = False
    else:
        print("Case 4: no config subfolder and no other changes")
        use_cases = []
        deploy = False

    use_cases_json = json.dumps(use_cases)

    print(f"deploy flag is set to {deploy}")
    print(f"use case is {use_cases_json}")

    with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
        print(f"deploy={str(deploy).lower()}", file=f)
        print(f"matrix={use_cases_json}", file=f)
        print("all_changed<<__GH_DELIM__", file=f)
        print(all_changed, file=f)            # safe multi-line write
        print("__GH_DELIM__", file=f)
        print(f"has_errors={str(has_errors).lower()}", file=f)


    # Validate changes
    if validate:
        print(f"Deploy: {str(deploy).lower()}")
        print(f"Has errors: {str(has_errors).lower()}")
        print(f"All changed: {all_changed}")
        if has_errors:
            print("::error:: Deployment is not valid.")
            print("Please check the changes in the PR.")
            print("If you want to deploy, make sure to:")
            print("1. Update the config files (just one subfolder per deploy) or the assets files, but not both scenarios at the same PR.")
            print("2. Remove the temp files.")
            sys.exit(1)
        else:
            print("Deployment is valid.")


if __name__ == "__main__":
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        sys.exit(f"Use: {sys.argv[0]} BASE_SHA HEAD_SHA [VALIDATE]")

    BASE_SHA = sys.argv[1]
    HEAD_SHA = sys.argv[2]
    VALIDATE_STR = sys.argv[3] if len(sys.argv) == 4 else "false"
    VALIDATE = VALIDATE_STR.lower() in ("1", "true", "yes")

    print(f"BASE_SHA: {BASE_SHA}")
    print(f"HEAD_SHA: {HEAD_SHA}")
    print(f"VALIDATE: {VALIDATE}")

    run(BASE_SHA, HEAD_SHA, VALIDATE)
