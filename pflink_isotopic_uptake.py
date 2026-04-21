import os
import sys
import argparse
from rich_argparse import RichHelpFormatter
import yaml

from HXMS_IO import write_hxms_file
from Parsers import FlagsParser, _parse_dynamX, _parse_HDXWorkbench, _parse_biopharma, _parse_HDExaminer, \
    _parse_custom


RED = "\033[91m"
RESET = "\033[0m"

def main():
    parser = argparse.ArgumentParser(
        description="Process raw H/D exchange mass spectrometry data into HXMS file format.",
        formatter_class=lambda prog: RichHelpFormatter(prog, max_help_position=200, width=400)
    )

    parser.add_argument("--input_csv_path", type=str, required=False,
                        help="Path to the file containing the raw input CSV/data files.")
    parser.add_argument("--output_hxms_path", type=str, required=False,
                        help="Path to the output directory where the final .hxms files will be saved.")
    parser.add_argument("--flags_file_path", type=str, required=False,
                        help="Path to a flags or configuration file to override default settings.")
    parser.add_argument("--peptide_list", type=str, required=False,
                        help="Path to a CSV file containing a list of peptides to filter or process.")
    parser.add_argument("--saturation", type=float, required=False,
                        help="The D2O saturation percentage (0.0 to 1.0) to record in the file header.")
    parser.add_argument("--ph", type=float, required=False,
                        help="The measured pH (pD read) value of the exchange buffer.")
    parser.add_argument("--temperature", type=float, required=False,
                        help="The temperature of the exchange reaction in Kelvin (K).")
    parser.add_argument("--protein_name", type=str, required=False,
                        help="The name of the protein.")
    parser.add_argument("--protein_state", type=str, required=False,
                        help="The experimental state of the protein (e.g., 'Apo', 'Bound', 'Mutant').")
    parser.add_argument("--protein_sequence", type=str, required=False,
                        help="The full amino acid sequence of the protein.")


    parser.add_argument("--include_exclude",
                        type=str,
                        required=False,
                        choices=['include', 'exclude'],
                        default=None,
                        help="Determines if the peptide list file should be used to include or exclude peptides from processing.")
    parser.add_argument("--file_type",
                        type=str,
                        required=False,
                        choices=["DynamX", "HDXworkbench", "HDExaminer", "BioPharma","Custom"],
                        default=None,
                        help="Input CSV format type")

    parser.add_argument("--config_yml",
                        type=str,
                        required=False,
                        help="Path to a YAML configuration file containing all parameters.")
    # Config YML Example:

    # input_csv_path: data / input.csv
    # output_hxms_path: results /
    # flags_file_path: null
    # peptide_list: peptides.csv
    # saturation: 0.6
    # ph: 7.2
    # temperature: 293.5
    # protein_name: MyProtein
    # protein_state: Apo
    # protein_sequence: AAGWDGA
    # file_type: HDXworkbench
    # include_exclude: include

    args = parser.parse_args()

    # Load configuration from YAML if provided
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

    INPUT_PATH = args.input_csv_path or config.get("input_csv_path")
    OUTPUT_PATH = args.output_hxms_path or config.get("output_hxms_path")
    FLAGS_PATH = args.flags_file_path or config.get("flags_file_path")
    PEPTIDE_LIST_PATH = args.peptide_list or config.get("peptide_list")

    # Validate required parameters after merging CLI and YAML
    if INPUT_PATH is None:
        print(f"{RED}Error: 'input_csv_path' must be provided via CLI or YAML.{RESET}")
        parser.print_help()
        sys.exit(1)
    if OUTPUT_PATH is None:
        print(f"{RED}Error: 'output_hxms_path' must be provided via CLI or YAML.{RESET}")
        parser.print_help()
        sys.exit(1)

    if INPUT_PATH is None or not os.path.isfile(INPUT_PATH):
        print(f"{RED}Error: Your input path '{INPUT_PATH}' does not exist or is not a file! Please correct it and run again.{RESET}")
        sys.exit(1)

    if OUTPUT_PATH is None or not os.path.isdir(OUTPUT_PATH):
        print(f"{RED}Error: Your output path '{OUTPUT_PATH}' does not exist or is not a directory! Please correct it and run again.{RESET}")
        sys.exit(1)

    if FLAGS_PATH:
        if not os.path.isfile(FLAGS_PATH):
            print(f"{RED}Error: The table file '{FLAGS_PATH}' does not exist! Please correct it and run again.{RESET}")
            parser.print_help()
            sys.exit(1)
    if PEPTIDE_LIST_PATH:
        if not os.path.isfile(PEPTIDE_LIST_PATH):
            print(f"{RED}Error: The peptide path '{PEPTIDE_LIST_PATH}' does not exist or is not a file! Please correct it and run again.{RESET}")
            sys.exit(1)

    if FLAGS_PATH:
        parser_flags = FlagsParser(FLAGS_PATH)
        flags = parser_flags.parse()

        protein_name_state_info = flags['protein_name_states']
        if protein_name_state_info is None:
            print("You must have a protein name and state in your flags. Example: [['Protein1' 'State1'],['Protein1' 'State2'],['Protein2' 'State3']]")
            parser.print_help()
            sys.exit(1)
        try:
            if len(protein_name_state_info[0]) != 2:
                print("You must have a protein name and state in your flags. Example: ['Protein' 'State']")
                parser.print_help()
                sys.exit(1)
        except:
            print("You must have a protein name and state in your flags. Example: ['Protein' 'State']")
            parser.print_help()
            sys.exit(1)

        protein_sequence_info = flags['protein_sequence']
        if protein_sequence_info is None:
            print("You must have a protein sequence in your flags. Example: ['AAGWDGA']")
            parser.print_help()
            sys.exit(1)

        d20_saturation = flags['d20_saturation']
        if d20_saturation is None:
            print("You must have a d20_saturation in your flags. Example: 0.6")
            parser.print_help()
            sys.exit(1)
        try:
            d20_saturation = float(d20_saturation)
            if d20_saturation > 1 or d20_saturation < 0:
                print("Your d20_saturation must be a float between 0 and 1 inclusive. Example: 0.6")
                parser.print_help()
                sys.exit(1)
        except:
            print("Your d20_saturation must be a float. Example: 0.6")
            parser.print_help()
            sys.exit(1)

        temp = flags['temp']
        if temp is None:
            print("You must have a temp (in K) in your flags. Example: 293.5")
            parser.print_help()
            sys.exit(1)
        try:
            temp = float(temp)
        except:
            print("You must have a temp (in K) in your flags that is an int or float. Example: 293.5")
            parser.print_help()
            sys.exit(1)
        ph = flags['ph']
        if ph is None:
            print("You must have a ph in your flags. Example: 7.2")
            parser.print_help()
            sys.exit(1)
        try:
            ph = float(ph)
        except:
            print("You must have a ph in your flags that is an int or float. Example: 7.2")
            parser.print_help()
            sys.exit(1)
        file_type = flags['file_type']
        if len(flags['protein_sequence']) == 1:
            flags['protein_sequence'] = flags['protein_sequence'][0]
        if file_type is None:
            print("You must choose a file type!")
            parser.print_help()
            sys.exit(1)


    else:
        saturation = args.saturation or config.get("saturation")
        ph = args.ph or config.get("ph")
        temperature = args.temperature or config.get("temperature")
        protein_name = args.protein_name or config.get("protein_name")
        protein_state = args.protein_state or config.get("protein_state")
        protein_sequence = args.protein_sequence or config.get("protein_sequence")
        file_type = args.file_type or config.get("file_type")
        if saturation is None:
            print("You must provide a saturation value!")
            parser.print_help()
            sys.exit(1)
        if ph is None:
            print("You must provide a ph value!")
            parser.print_help()
            sys.exit(1)
        if temperature is None:
            print("You must provide a temperature value!")
            parser.print_help()
            sys.exit(1)
        if protein_name is None:
            print("You must provide a protein_name value!")
            parser.print_help()
            sys.exit(1)
        if protein_state is None:
            print("You must provide a protein_state value!")
            parser.print_help()
            sys.exit(1)
        if protein_sequence is None:
            print("You must provide a protein_sequence value!")
            parser.print_help()
            sys.exit(1)
        if file_type is None:
            print("You must provide a file_type value!")
            parser.print_help()
            sys.exit(1)
        flags = {
            'protein_name_states': [protein_name + " " + protein_state],
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
        "HDExaminer": _parse_HDExaminer,
        "Custom": _parse_custom,
    }

    if file_type in parser_map:
        hxms = parser_map[file_type](INPUT_PATH, flags)
        if hxms:
            hxms_good = write_hxms_file(hxms, OUTPUT_PATH, flags, None, None, PEPTIDE_LIST_PATH, include_exclude, None, None,True)
            if not hxms_good:
                print("Error while generating file. Please check your inputs!")


if __name__ == "__main__":

    main()