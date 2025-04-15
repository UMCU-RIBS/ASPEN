from logging import getLogger
from json import dump
from os import environ
from numpy import linspace, r_, tile
from pathlib import Path
from shutil import move, copyfile, copyfileobj
from subprocess import run, DEVNULL
from tempfile import mkstemp, gettempdir
import gzip

from ..nibabel import save as nisave
from ..nibabel import load as niload
from ..bidso.utils import replace_extension

from .io.parrec import convert_parrec_nibabel
from .utils import rename_task, make_bids_name, find_one_file, make_taskdescription, set_notnone

lg = getLogger(__name__)

# DIRECTION might depend on the way that the data is stored in Nifti file.
# Hopefully nibabel is consistent in how it converts the data but we need to check (also the sign of qform)
DIRECTION = {
    'RL': 'i',
    'LR': 'i-',
    'PA': 'j',
    'AP': 'j-',
    'IS': 'k',
    'SI': 'k-',
    }


def convert_mri(run, rec, dest_path, name, deface=True):
    """Return base name for this run"""
    output_nii = dest_path / f'{make_bids_name(name)}_{rec.modality}.nii.gz'

    file = find_one_file(rec, ('parrec', ))
    if file is not None:
        input_nii, PAR = convert_parrec_nibabel(file.path, MagneticFieldStrength=run.session.MagneticFieldStrength)
        move(input_nii, output_nii)

    else:
        file = find_one_file(rec, ('nifti', ))
        PAR = None
        if file is None:
            return None

        else:
            input_nii = file.path

            if input_nii.name.endswith('.nii.gz'):
                copyfile(file.path, output_nii)
            elif input_nii.name.endswith('.nii'):
                gz(file.path, output_nii)
            else:
                lg.warning(f'Unknown extension for nifti for {input_nii}')
                return None

    if run.task_name == 'MP2RAGE':
        lg.info('Keeping only the first volume for MP2RAGE')
        select(output_nii, 'first')

    nii_shape = _fix_tr(output_nii, rec)

    if PAR is not None and 'phase' in PAR['image_types']:
        phase_file = dest_path / f'{make_bids_name(name)}_phase.nii.gz'
        lg.info(f'Splitting phase info to {phase_file.name}')
        phase_nii = select(output_nii, 'split')
        phase_nii.to_filename(phase_file)

    if deface and rec.modality in ('T1w', 'T2w', 'T2star', 'PD', 'FLAIR'):
        run_deface(output_nii)

    sidecar = _convert_sidecar(run, rec, PAR, nii_shape)
    sidecar_file = replace_extension(output_nii, '.json')

    with sidecar_file.open('w') as f:
        dump(sidecar, f, indent=2)

    return output_nii


def select(nii, slicing):
    """If slicing is "split", it returns the nifti of the second half"""
    img = niload(nii)
    half = int(img.shape[3] / 2)
    secondhalf = None

    if slicing == 'first':
        img = img.slicer[:, :, :, 0]

    elif slicing == 'firsthalf':
        img = img.slicer[:, :, :, :half]

    elif slicing == 'secondhalf':
        img = img.slicer[:, :, :, half:]

    elif slicing == 'split':
        secondhalf = img.slicer[:, :, :, half:]
        img = img.slicer[:, :, :, :half]

    img.to_filename(nii)

    return secondhalf


def _fix_tr(nii, rec):
    """
    Returns
    -------
    tuple
        shape of the nifti file
    """
    img = niload(str(nii))

    # this seems a bug in nibabel. It stores time in sec, not in msec
    img.header.set_xyzt_units('mm', 'sec')

    if rec.modality in ('bold', 'epi') and rec.RepetitionTime is not None:
        img.header['pixdim'][4] = rec.RepetitionTime

    nisave(img, str(nii))

    return img.shape


def _convert_sidecar(run, rec, hdr=None, shape=None):
    D = {
        'InstitutionName': 'University Medical Center Utrecht',
        'InstitutionAddress': 'Heidelberglaan 100, 3584 CX Utrecht, the Netherlands',
        }

    if run.session.MagneticFieldStrength is not None:
        D['MagneticFieldStrength'] = float(run.session.MagneticFieldStrength[:-1])

    if rec.PhaseEncodingDirection is not None:
        D['PhaseEncodingDirection'] = DIRECTION[rec.PhaseEncodingDirection]
    if rec.SliceEncodingDirection is not None:
        D['SliceEncodingDirection'] = DIRECTION[rec.SliceEncodingDirection]

    for field in 'EchoTime', 'EffectiveEchoSpacing', 'FlipAngle':
        set_notnone(D, hdr, field)

    for field in 'Sequence', 'MultibandAccelerationFactor':
        set_notnone(D, rec, field)

    if rec.modality in ('bold', 'epi'):
        set_notnone(D, hdr, 'RepetitionTime')  # first get RepetitionTime from Header,
        set_notnone(D, rec, 'RepetitionTime')  # then, use the one specified in rec
        D['TaskName'] = rename_task(run.task_name)
        D['TaskDescription'] = make_taskdescription(run)

        if hdr is not None:
            add_slicetiming(D, hdr, rec)
        if shape is not None and 'EffectiveEchoSpacing' in D and 'PhaseEncodingDirection' in D:
            NIFTI_INDEX = {'i': 0, 'j': 1, 'k': 2}
            ReconMatrixPE = shape[NIFTI_INDEX[D['PhaseEncodingDirection'][0]]]
            D['TotalReadoutTime'] = D['EffectiveEchoSpacing'] * (ReconMatrixPE - 1)

    return D


def add_slicetiming(D, hdr, rec):
    """

    TODO
    ----
    Is there a SliceTiming when the SliceOrder is 3D?
    """
    if rec.SliceOrder is None:
        lg.warning(f'Please specify SliceOrder for Recording(db, id={rec.id})')
        return

    elif rec.SliceOrder == '3D':
        return

    # get TR from SQL, but if it's not specified used PAR/REC
    TR = D.get('RepetitionTime', hdr['RepetitionTime'])

    n_slices = hdr['n_slices']

    multiband = D.get('MultibandAccelerationFactor', 1)
    n_slices = int(n_slices / multiband)

    SliceTiming = linspace(0, TR, n_slices + 1)[:-1]

    if rec.SliceOrder == 'Interleaved':
        SliceTiming = r_[SliceTiming[::2], SliceTiming[1::2]]

    SliceTiming = tile(SliceTiming, multiband)
    D['SliceTiming'] = SliceTiming.tolist()


def run_deface(nii):
    lg.info(f'Defacing {nii.name}, it might take a while')
    path_avg = Path(environ['FREESURFER_HOME']) / 'average'

    # generate a unique file name in the same folder
    if nii.name.endswith('.nii.gz'):
        suffix = '.nii.gz'
    elif nii.name.endswith('.nii'):
        suffix = '.nii'
    nii_tmp = Path(mkstemp(dir=nii.parent, suffix=suffix)[1])
    nii_tmp.unlink()

    run([
        'mri_deface',  # from freesurfer
        nii,
        path_avg / 'talairach_mixed_with_skull.gca',
        path_avg / 'face.gca',
        nii_tmp],
        stdout=DEVNULL, stderr=DEVNULL,
        cwd=gettempdir(),
        )

    nii_tmp.rename(nii)


def gz(input_file, output_file):
    with input_file.open('rb') as f_in:
        with gzip.open(output_file, 'wb') as f_out:
            copyfileobj(f_in, f_out)
