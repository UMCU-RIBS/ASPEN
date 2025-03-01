from itertools import chain


def anonymize_subjects(bids_dir, subj_code=None):
    """

    Parameters
    ----------
    bids_dir : path
        path to bids folder
    subj_code : dict
        keys are current subject names and values are new subject names, f.e. {'sub-oldname': 'sub-001'}
        If it's not specified, then the first subject in alphabetical order will be sub-001 etc.
    """
    if subj_code is None:
        subj_code = {k.name: f"sub-{i + 1:03d}" for i, k in enumerate(sorted(bids_dir.glob('sub-*')))}

    TEXT_FILES = chain(
        bids_dir.glob('**/*.tsv'),
        bids_dir.glob('**/*.vhdr'),
        bids_dir.glob('**/*.vmrk'),
        bids_dir.glob('**/*.json'),
        )

    for tsv_file in TEXT_FILES:
        with tsv_file.open() as f:
            txt = f.read()
        for old, new in subj_code.items():
            txt = txt.replace(old, new)
        with tsv_file.open('w') as f:
            f.write(txt)

    for subj_path in bids_dir.glob('sub-*'):
        txt = subj_path.name
        for old, new in subj_code.items():
            txt = txt.replace(old, new)

        new_subj_path = subj_path.parent / txt
        subj_path.rename(new_subj_path)

    for old_file in bids_dir.glob('**/*.*'):
        txt = old_file.name
        for old, new in subj_code.items():
            txt = txt.replace(old, new)
        old_file.rename(old_file.parent / txt)
