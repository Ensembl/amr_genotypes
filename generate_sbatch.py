#!/usr/bin/env python3

import argparse
from math import ceil
from pathlib import Path
from itertools import islice


def batched(iterable, n):
    if n < 1:
        raise ValueError("n must be at least 1")
    it = iter(iterable)
    while True:
        batch = list(islice(it, n))
        if not batch:
            return
        yield batch


def generate_directory_structure(base_dir: Path):
    print("Setting up directories")
    dir_names = [
        "logs",
        "parsed/assembly",
        "parsed/genotype",
        "parsed/genotype/parquet",
        "parsed/phenotype",
    ]
    for dir in dir_names:
        new_dir = base_dir / dir
        print(f"  > Creating dir {new_dir}")
        new_dir.mkdir(parents=True, exist_ok=True)


def files_to_process(to_process: Path, previously_processed: Path = None) -> list[str]:
    lookup = {}
    gff_files = []
    if previously_processed:
        with open(previously_processed, "rt") as fh:
            for gff in fh:
                lookup[gff.strip()] = True
    with open(to_process, "rt") as fh:
        for gff in fh:
            gff = gff.strip()
            if gff not in lookup:
                gff_files.append(gff)
    return gff_files


def split_list_and_write(base_dir: Path, files: list[str]) -> int:
    split_count = 0
    batch_size = 5000
    print(
        f"Splitting {len(files)} GFF(s) into {ceil(len(files)/batch_size)} batches of {batch_size}"
    )
    for batch in batched(files, batch_size):
        path = f"split.gff.{split_count:0>2}"
        with open(base_dir / path, "wt") as fh:
            print(f"  > Writing to {base_dir / path}")
            for gff in batch:
                fh.write(f"{gff}\n")
        split_count += 1
    return split_count


def write_template(args, split_count: int):
    current_dir = Path(__file__).parent.absolute()
    with open(current_dir / "templates" / "sbatch.template") as fh:
        template = fh.read()
    template = template.replace("{PARSE_AMR_PY}", str(current_dir / "parse_amr.py"))
    template = template.replace("{BASE_DIR}", str(args.base_dir.absolute()))
    template = template.replace("{EMAIL}", args.email)
    template = template.replace("{JOB_NAME}", args.job_name)
    template = template.replace("{QUEUE}", args.queue)
    template = template.replace("{MEMORY}", args.memory)
    template = template.replace("{TOTAL_FILES}", f"{split_count-1:0>2}")
    print(f"Writing new template to {args.output}")
    with open(args.output, "wt") as fh:
        fh.write(template)


def arg_parser():
    parser = argparse.ArgumentParser(
        description="Create a directory structure and files as expected for working with the AMR genotypes"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        required=True,
        help="Path or URL to the base directory for files",
    )
    parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="Your email address",
    )
    parser.add_argument(
        "--job-name",
        type=str,
        required=False,
        help="Job name in slurm",
        default="parse_genotype_gffs",
    )
    parser.add_argument(
        "--queue",
        type=str,
        required=False,
        default="production",
        help="Queue to submit to",
    )
    parser.add_argument(
        "--to-process",
        type=Path,
        required=True,
        help="The GFFs to process",
    )
    parser.add_argument(
        "--previously-processed",
        type=Path,
        required=False,
        help="List of GFF files that were previously processed",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Where to write the template to",
    )
    parser.add_argument(
        "--memory",
        type=str,
        required=False,
        default="16G",
        help="Memory to reserve",
    )
    return parser


def main():
    parser = arg_parser()
    args = parser.parse_args()
    generate_directory_structure(args.base_dir)
    files = files_to_process(args.to_process, args.previously_processed)
    split_count = split_list_and_write(args.base_dir, files)
    write_template(args, split_count)
    print(f"✅ Script finished")


if __name__ == "__main__":
    main()
