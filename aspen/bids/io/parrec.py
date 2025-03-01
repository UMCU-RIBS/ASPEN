from logging import getLogger
from pathlib import Path
from numpy import unique
from nibabel.parrec import parse_PAR_header
from nibabel.cmdline.parrec2nii import get_opt_parser, proc_file, verbose
from nibabel.mriutils import calculate_dwell_time
from tempfile import mkdtemp

lg = getLogger(__name__)

MR_TYPES = {
    0: 'magnitude',
    3: 'phase',
    -1: 'reconstructed',  # relevant for MP2RAGE
    }

def convert_parrec_nibabel(par_file, MagneticFieldStrength=None):
    """

    """
    input_par = Path(par_file).resolve()
    hdr = parse_PAR(input_par, MagneticFieldStrength)

    tmp_dir = mkdtemp()
    lg.debug(f'Temporary directory for PAR/REC conversion: {tmp_dir}')

    parser = get_opt_parser()
    (opts, infiles) = parser.parse_args([
        '--output-dir=' + tmp_dir,
        '--compressed',
        '--permit-truncated',
        '--store-header',
        '--strict-sort',  # necessary for magnitute / phase
        ] + [str(input_par), ]
        )
    verbose.switch = opts.verbose

    proc_file(infiles[0], opts)

    output = next(Path(tmp_dir).glob('*.nii.gz'))

    return output, hdr


def parse_PAR(par_file, MagneticFieldStrength=None):
    """Get some useful information from PAR file. It's quite slow but reading
    the PAR file twice seems the best solution.

    Returns
    -------
    dict
        "n_dynamics" : int
            actual number of recorded dynamics (not the planned number of dyns)
        "EffectiveEchoSpacing" : float
            use nibabel to compute EffectiveEchoSpacing (dwell time in nibabel is not the same as DwellTime in BIDS)
    """
    out = {}
    with par_file.open() as f:
        hdr, info = parse_PAR_header(f)

    out['RepetitionTime'] = hdr['repetition_time'].item() / 1000
    out['n_dynamics'] = info['dynamic scan number'].max()
    out['EchoTime'] = info['echo_time'][0] / 1000  # ms -> s
    out['n_slices'] = info['slice number'].max()
    out['FlipAngle'] = info['image_flip_angle'][0]
    if MagneticFieldStrength is not None:
        MagneticFieldStrength = float(MagneticFieldStrength[:-1])
        out['EffectiveEchoSpacing'] = calculate_dwell_time(hdr['water_fat_shift'], hdr['epi_factor'], MagneticFieldStrength) / 1000

    try:
        out['image_types'] = [MR_TYPES[x] for x in unique(info['image_type_mr'])]
    except KeyError:
        raise ValueError('Unrecognized "image_type_mr" in PAR file. Please add it to MR_TYPES in this function')

    return out
