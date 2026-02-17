import re

def extract_tags(text):
    """
    Extracts tags from text.
    Supports:
    - Placeholders: {0}, {1}
    - XML/HTML tags: <b>, </b>, <br/>, <img src="..."/>
    """
    if not text:
        return []
        
    # Pattern for placeholders {n} and XML-like tags <...>
    # Note: we want to match the whole tag including <> or {}
    pattern = r'(\{\d+\})|(<\/?[^>]+>)'
    
    matches = re.findall(pattern, text)
    # Combine results from both capturing groups
    return [m[0] or m[1] for m in matches]

def validate_tags(source_text, target_text):
    """
    Checks if target_text contains the same tags as source_text.
    
    Returns:
        tuple: (is_valid, missing_tags, extra_tags)
    """
    src_tags = extract_tags(source_text)
    tgt_tags = extract_tags(target_text)
    
    if not src_tags and not tgt_tags:
        return True, [], []
        
    # Count occurrences of each tag
    src_counts = {}
    for t in src_tags:
        src_counts[t] = src_counts.get(t, 0) + 1
        
    tgt_counts = {}
    for t in tgt_tags:
        tgt_counts[t] = tgt_counts.get(t, 0) + 1
        
    missing = []
    for t, count in src_counts.items():
        if tgt_counts.get(t, 0) < count:
            missing.append(t)
            
    extra = []
    for t, count in tgt_counts.items():
        if t not in src_counts: # Any tag not in source is extra
             extra.append(t)
        elif tgt_counts[t] > src_counts[t]: # More occurrences than source
             extra.append(t)
             
    # Unique lists for notification
    return (len(missing) == 0 and len(extra) == 0), list(set(missing)), list(set(extra))
