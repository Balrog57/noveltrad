import sys

def cleanup(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Ranges to remove (1-indexed, inclusive)
    # Based on previous view_file (L950 total)
    # IMPORTANT: Delete from bottom to top
    ranges = [
        (920, 928), # show_search_replace
        (817, 820), # show_alignment_dialog
        (822, 837), # show_qa_dialog
        (701, 734), # auto_structure_chapters (Obsolete since Phase 1)
        (648, 656), # show_statistics_dialog
        (639, 647), # open_glossary_manager
        (615, 637), # import_dictionary
        (588, 614), # on_dictionary_search
        (556, 581)  # on_word_lookup
    ]

    for start, end in ranges:
        del lines[start-1:end]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"Removed {sum(e-s+1 for s,e in ranges)} lines from {file_path}")

if __name__ == "__main__":
    cleanup(sys.argv[1])
