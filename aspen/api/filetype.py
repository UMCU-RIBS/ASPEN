from pathlib import Path
from ..gui.utils import _throw_msg_box


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

    # ASP-162 Support for Palmtree
    elif suffix == '.src':
        data_type = 'palmtree'

    elif suffix == '.nev':
        data_type = 'blackrock'

    elif suffix in ('.ns1', '.ns2', '.ns3', '.ns4', '.ns5', '.ns6', '.ns7', '.ns8', '.ns9',):  # ASP-194 unsupported
        _throw_msg_box("Unsupported filetype detected!",
                       ".ns(1-9) files no longer supported please use .nev files")
        data_type = 'unsupported'

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

    # ASP-109 .mat files being put on electrodes or cortex depending on name
    # You could get away with one if statement, but I am assuming we will have to check for matlab names soon.
    elif suffix == '.mat':
        file_name = Path(file_path).name.lower()
        if file_name.find("electrodes") != -1:
            data_type = 'Electrodes'
        elif file_name.find("cortex") != -1:
            data_type = 'Cortex'
        else:
            data_type = 'Electrodes'

    else:
        raise ValueError(f'Unknown file suffix "{suffix}"')

    return data_type
