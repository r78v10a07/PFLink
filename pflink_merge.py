import argparse
import sys
from rich_argparse import RichHelpFormatter
import os
import yaml

from HXMS_IO import HxmsData
from Helper_Functions import combine_hxms_data
from Parsers import validate_and_parse_hxms_file


RED = "\033[91m"
RESET = "\033[0m"

def main():


    parser = argparse.ArgumentParser(
        description="Process HX-MS data.",
        formatter_class=lambda prog: RichHelpFormatter(prog, max_help_position=200, width=400)
    )

    parser.add_argument("--input_hxms_path1", type=str, required=False,
                        help="Path to the file1 containing the.hmxs data")
    parser.add_argument("--input_hxms_path2", type=str, required=False,
                        help="Path to the file2 containing the.hmxs data")
    parser.add_argument("--output_hxms_path", type=str, required=False,
                        help="Path to the output directory where the final .hxms files will be saved.")
    parser.add_argument("--config_yml",
                        type=str,
                        required=False,
                        help="Path to YAML config file with all parameters.")

    # Config YML Example:

    # input_hxms_path1: "/path/to/file1.hxms"
    # input_hxms_path2: "/path/to/file2.hxms"
    # output_hxms_path: "/path/to/output_dir"

    args = parser.parse_args()

    config = {}
    if args.config_yml:
        if not os.path.isfile(args.config_yml):
            print(f"{RED}Error: Config file '{args.config_yml}' does not exist!{RESET}")
            sys.exit(1)
        try:
            with open(args.config_yml, "r") as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"{RED}Error reading YAML config: {e}{RESET}")
            sys.exit(1)

    INPUT_PATH1 = args.input_hxms_path1 or config.get("input_hxms_path1")
    INPUT_PATH2 = args.input_hxms_path2 or config.get("input_hxms_path2")
    OUTPUT_PATH = args.output_hxms_path or config.get("output_hxms_path")

    if INPUT_PATH1 is None:
        print(f"{RED}Error: input_hxms_path1 must be provided (CLI or YAML){RESET}")
        sys.exit(1)
    if INPUT_PATH2 is None:
        print(f"{RED}Error: input_hxms_path2 must be provided (CLI or YAML){RESET}")
        sys.exit(1)
    if OUTPUT_PATH is None:
        print(f"{RED}Error: output_hxms_path must be provided (CLI or YAML){RESET}")
        sys.exit(1)

    if INPUT_PATH1 is None or not os.path.isfile(INPUT_PATH1):
        print(f"{RED}Error: Your input path '{INPUT_PATH1}' does not exist or is not a file! Please correct it and run again.{RESET}")
        sys.exit(1)
    if INPUT_PATH2 is None or not os.path.isfile(INPUT_PATH2):
        print(f"{RED}Error: Your input path '{INPUT_PATH2}' does not exist or is not a file! Please correct it and run again.{RESET}")
        sys.exit(1)
    if OUTPUT_PATH is None or not os.path.isdir(OUTPUT_PATH):
        print(f"{RED}Error: Your output path '{OUTPUT_PATH}' does not exist or is not a directory! Please correct it and run again.{RESET}")
        sys.exit(1)

    hxms_data_1 = validate_and_parse_hxms_file(INPUT_PATH1)
    hxms_data_2 = validate_and_parse_hxms_file(INPUT_PATH2)
    if (not hxms_data_1[0]) or (not hxms_data_2[0]):
        print("One of your hxms files are wrong. Please fix them before trying to merge.")
        exit()

    hxms_1_hxms_object: HxmsData = hxms_data_1[2]
    hxms_2_hxms_object: HxmsData = hxms_data_2[2]
    
    if hxms_1_hxms_object.proteins != hxms_2_hxms_object.proteins:
        print("Your protein names do no match. Please sure you are using the same protein and try again.")
        exit()
    if hxms_1_hxms_object.state != hxms_2_hxms_object.state:
        print("Your protein states do no match. Please sure you are using the same state and try again.")
        exit()
    if hxms_1_hxms_object.metadata['protein_sequence'] != hxms_2_hxms_object.metadata['protein_sequence']:
        print("Your protein sequences do no match. Please sure you are using the same sequence and try again.")
        exit()
    if hxms_1_hxms_object.metadata['temperature'] != hxms_2_hxms_object.metadata['temperature']:
        print("Your temperatures do no match. Please sure you are using the same temperature and try again.")
        exit()
    if hxms_1_hxms_object.metadata['ph'] != hxms_2_hxms_object.metadata['ph']:
        print("Your phs do no match. Please sure you are using the same phs and try again.", duration=30)
        exit()
    if hxms_1_hxms_object.metadata['saturation'] != hxms_2_hxms_object.metadata['saturation']:
        print("Your saturations do no match. Please sure you are using the same saturations and try again.")
        exit()

    out_hxms = combine_hxms_data(hxms_1_hxms_object, hxms_data_1[-1], hxms_2_hxms_object, hxms_data_2[-1])

    from HXMS_IO import write_hxms_file_combined_test
    write_hxms_file_combined_test(out_hxms, f"{hxms_1_hxms_object.metadata['protein_name']}_{hxms_1_hxms_object.metadata['protein_state']}_merged.hxms")



if __name__ == "__main__":
    main()