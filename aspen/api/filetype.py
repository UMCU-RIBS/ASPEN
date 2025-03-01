from pathlib import Path


def parse_filetype(file_path):

    data_file = Path(file_path)
    suffix = data_file.suffix.lower()

    if suffix == '.par':
        data_type = 'parrec'

    elif suffix == '.nii' or data_file.name.endswith('.nii.gz'):
        data_type = 'nifti'

    elif suffix == '.img':
        data_type = 'nifti'

    elif suffix == '.dat':
        data_type = 'bci2000'

    elif suffix == '.trc':
        data_type = 'micromed'

    # TODO get rid of the ns1..ns9 we wont need those just the nev file as it is the header
    elif suffix in ('.nev', '.ns1', '.ns2', '.ns3', '.ns4', '.ns5', '.ns6', '.ns7', '.ns8', '.ns9'):
        data_type = 'blackrock'

    elif suffix == '.pdf':
        data_type = 'pdf'

    elif suffix in ('.jpg', '.jpeg', '.png'):
        data_type = 'image'

    elif suffix in ('.doc', '.docx'):
        data_type = 'docx'

    elif suffix == '':
        data_type = 'dicom'

    # ASP-82 wave files were not built-in apparently
    elif suffix == '.wav':
        data_type = 'wave'

    else:
        raise ValueError(f'Unknown file suffix "{suffix}"')

    return data_type
