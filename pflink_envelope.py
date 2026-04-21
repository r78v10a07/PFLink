import os
import sys
import argparse
import yaml
from rich_argparse import RichHelpFormatter

from pigeon_feather.hxio import *

from HXMS_IO import write_hxms_file
from Helper_Functions import _conver_PFhxms_to_hxms
from Parsers import FlagsParser, _parse_dynamX, _parse_HDXWorkbench, _parse_biopharma, _parse_HDExaminer, \
    _parse_custom

RED = "\033[91m"
RESET = "\033[0m"

def main():


    parser = argparse.ArgumentParser(
        description="Process HX-MS data.",
        formatter_class=lambda prog: RichHelpFormatter(prog, max_help_position=200, width=400)
    )

    def fail(message: str):
        print(message)
        parser.print_help()
        sys.exit(1)


    parser.add_argument("--input_csv_path", type=str, required=False,
                        help="Path to the file containing the raw input CSV/data files.")
    parser.add_argument("--output_hxms_path", type=str, required=False,
                        help="Path to the output directory where the final .hxms files will be saved.")
    parser.add_argument("--flags_file_path", type=str, required=False,
                        help="Path to a flags or configuration file to override default settings.")
    parser.add_argument("--peptide_list", type=str, required=False,
                        help="Path to a CSV/TXT file containing a list of peptides to filter or process.")
    parser.add_argument("--raw_spectra_path", type=str, required=False,
                        help="Name of the HDExam spectra folder inside the input path.")

    parser.add_argument("--saturation", type=float, required=False,
                        help="The $\text{D}_2\text{O}$ saturation percentage (0.0 to 1.0) to record in the file header.")
    parser.add_argument("--ph", type=float, required=False,
                        help="The measured $\text{pH}$ ($\text{pD}$ read) value of the exchange buffer.")
    parser.add_argument("--temperature", type=float, required=False,
                        help="The temperature of the exchange reaction in Kelvin ($\text{K}$).")
    parser.add_argument("--protein_name", type=str, required=False,
                        help="The common or unique name of the protein.")
    parser.add_argument("--protein_state", type=str, required=False,
                        help="The experimental state of the protein (e.g., 'Apo', 'Bound', 'Mutant').")
    parser.add_argument("--protein_sequence", type=str, required=False,
                        help="The full amino acid sequence of the protein.")

    parser.add_argument("--save_match", action="store_true", required=False,
                        help="Whether to save the match data. Default is False.")
    parser.add_argument("--save_fine_match", action="store_true", required=False,
                        help="Whether to save the fine match data. Default is False.")

    parser.add_argument("--include_exclude",
                        type=str,
                        required=False,
                        choices=['include', 'exclude'],
                        default=None,
                        help="Determines if the peptide list file should be used to include or exclude peptides from processing.")
    parser.add_argument("--file_type",
                        type=str,
                        required=False,
                        choices=["HDExaminer"],
                        default=None,
                        help="Input CSV format type")

    parser.add_argument("--config_yml",
                        type=str,
                        required=False,
                        help="Path to YAML config file with all parameters.")

    # Config YML Example:

    # input_csv_path: "/path/to/input.csv"
    # output_hxms_path: "/path/to/output_dir"
    # raw_spectra_path: "/path/to/spectra_folder"
    # flags_file_path: null
    # peptide_list: null
    # saturation: 0.6
    # ph: 7.2
    # temperature: 293.5
    # protein_name: "MyProtein"
    # protein_state: "Apo"
    # protein_sequence: "AAGWDGA"
    # file_type: "HDExaminer"
    # include_exclude: "include"  # or "exclude"
    # save_match: false
    # save_fine_match: false

    args = parser.parse_args()

    config = {}
    if args.config_yml:
        if not os.path.isfile(args.config_yml):
            fail(f"{RED}Error: Config file '{args.config_yml}' does not exist!{RESET}")
        try:
            with open(args.config_yml, "r") as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            fail(f"{RED}Error reading YAML config: {e}{RESET}")

    INPUT_PATH = args.input_csv_path or config.get("input_csv_path")
    OUTPUT_PATH = args.output_hxms_path or config.get("output_hxms_path")
    FLAGS_PATH = args.flags_file_path or config.get("flags_file_path")
    PEPTIDE_LIST_PATH = args.peptide_list or config.get("peptide_list")
    RAW_SPEC_PATH = args.raw_spectra_path or config.get("raw_spectra_path")

    if INPUT_PATH is None:
        fail(f"{RED}Error: input_csv_path must be provided (CLI or YAML){RESET}")
    if OUTPUT_PATH is None:
        fail(f"{RED}Error: output_hxms_path must be provided (CLI or YAML){RESET}")
    if RAW_SPEC_PATH is None:
        fail(f"{RED}Error: raw_spectra_path must be provided (CLI or YAML){RESET}")

    if INPUT_PATH is None or not os.path.isfile(INPUT_PATH):
        fail(f"{RED}Error: Your input path '{INPUT_PATH}' does not exist or is not a file! Please correct it and run again.{RESET}")

    if OUTPUT_PATH is None or not os.path.isdir(OUTPUT_PATH):
        fail(f"{RED}Error: Your output path '{OUTPUT_PATH}' does not exist or is not a directory! Please correct it and run again.{RESET}")

    if RAW_SPEC_PATH is None or not os.path.isfile(RAW_SPEC_PATH):
        fail(f"{RED}Error: Your spectra path '{RAW_SPEC_PATH}' does not exist or is not a directory! Please correct it and run again.{RESET}")

    if FLAGS_PATH:
        if not os.path.isfile(FLAGS_PATH):
            fail(f"{RED}Error: The table file '{FLAGS_PATH}' does not exist! Please correct it and run again.{RESET}")
    if PEPTIDE_LIST_PATH:
        if not os.path.isfile(PEPTIDE_LIST_PATH):
            fail(f"{RED}Error: The peptide path '{PEPTIDE_LIST_PATH}' does not exist or is not a file! Please correct it and run again.{RESET}")

    if FLAGS_PATH:
        parser = FlagsParser(FLAGS_PATH)
        flags = parser.parse()

        protein_name_state_info = flags['protein_name_states']
        if protein_name_state_info is None:
            fail("You must have a protein name and state in your flags. Example: [['Protein1' 'State1'],['Protein1' 'State2'],['Protein2' 'State3']]")
        try:
            if len(protein_name_state_info[0]) != 2:
                fail("You must have a protein name and state in your flags. Example: ['Protein' 'State']")
        except:
            fail("You must have a protein name and state in your flags. Example: ['Protein' 'State']")
        protein_name = flags['protein_name_states'][0][0]
        protein_sequence = flags['protein_sequence']
        flags['protein_state'] = flags['protein_name_states'][0][1]
        if protein_sequence is None:
            fail("You must have a protein sequence in your flags. Example: ['AAGWDGA']")

        saturation = flags['d20_saturation']
        if saturation is None:
            fail("You must have a d20_saturation in your flags. Example: 0.6")
        try:
            saturation = float(saturation)
            if saturation > 1 or saturation < 0:
                fail("Your d20_saturation must be a float between 0 and 1 inclusive. Example: 0.6")
        except:
            fail("Your d20_saturation must be a float. Example: 0.6")

        temperature = flags['temp']
        if temperature is None:
            fail("You must have a temp (in K) in your flags. Example: 293.5")
        try:
            temperature = float(temperature)
        except:
            fail("You must have a temp (in K) in your flags that is an int or float. Example: 293.5")
        ph = flags['ph']
        if ph is None:
            fail("You must have a ph in your flags. Example: 7.2")
        try:
            ph = float(ph)
        except:
            fail("You must have a ph in your flags that is an int or float. Example: 7.2")
        file_type = flags['file_type']
        if len(flags['protein_sequence']) == 1:
            flags['protein_sequence'] = flags['protein_sequence'][0]
        if file_type is None:
            fail("You must choose a file type!")


    else:
        saturation = args.saturation or config.get("saturation")
        ph = args.ph or config.get("ph")
        temperature = args.temperature or config.get("temperature")
        protein_name = args.protein_name or config.get("protein_name")
        protein_state = args.protein_state or config.get("protein_state")
        protein_sequence = args.protein_sequence or config.get("protein_sequence")
        file_type = args.file_type or config.get("file_type")
        if saturation is None:
            fail("You must provide a saturation value!")
        if ph is None:
            fail("You must provide a ph value!")
        if temperature is None:
            fail("You must provide a temperature value!")
        if protein_name is None:
            fail("You must provide a protein_name value!")
        if protein_state is None:
            fail("You must provide a protein_state value!")
        if protein_sequence is None:
            fail("You must provide a protein_sequence value!")
        if file_type is None:
            fail("You must provide a file_type value!")
        flags = {
            'protein_name_states': [protein_name + " " + protein_state],
            'protein_state': protein_state,
            'protein_sequence': protein_sequence,
            'ph': ph,
            'd20_saturation': saturation,
            'temp': temperature,
            'file_type': file_type
        }
    include_exclude = None
    if PEPTIDE_LIST_PATH:
        include_exclude = args.include_exclude or config.get("include_exclude")
        if include_exclude == "include":
            include_exclude = True
        else:
            include_exclude = False
    parser_map = {
        "DynamX": _parse_dynamX,
        "HDXworkbench": _parse_HDXWorkbench,
        "BioPharma": _parse_biopharma,
#        "Byos": _parse_byos,
        "HDExaminer": _parse_HDExaminer,
        "Custom": _parse_custom,
    }


    save_match = args.save_match or args.save_fine_match
    if file_type in parser_map:
        hxms = _conver_PFhxms_to_hxms(INPUT_PATH,protein_sequence,saturation,ph,temperature,RAW_SPEC_PATH,protein_name, flags['protein_state'])
        if hxms:
            hxms_good = write_hxms_file(hxms, OUTPUT_PATH, flags, None, None, PEPTIDE_LIST_PATH, include_exclude, None, None,True, save_match, args.save_fine_match)
            if not hxms_good:
                print("Error while generating file. Please check your inputs!")


if __name__ == "__main__":
    main()