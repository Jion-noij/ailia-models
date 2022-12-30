import os
import sys
import time

import numpy as np
import cv2

import ailia

import random

# import original modules
sys.path.append('../../util')
from utils import get_base_parser, update_parser, get_savepath  # noqa
from model_utils import check_and_download_models, urlretrieve, progress_print  # noqa
# logger
from logging import getLogger  # noqa

logger = getLogger(__name__)


# ======================
# Parameters
# ======================

WEIGHT_UNET_PATH = 'unet.onnx'
WEIGHT_PB_UNET_PATH = 'weights.pb'
MODEL_UNET_PATH = 'unet.onnx.prototxt'
WEIGHT_SAFETY_CHECKER_PATH = 'safety_checker.onnx'
MODEL_SAFETY_CHECKER_PATH = 'safety_checker.onnx.prototxt'
WEIGHT_TEXT_ENCODER_PATH = 'text_encoder.onnx'
MODEL_TEXT_ENCODER_PATH = 'text_encoder.onnx.prototxt'
WEIGHT_VAE_ENCODER_PATH = 'vae_encoder.onnx'
MODEL_VAE_ENCODER_PATH = 'vae_encoder.onnx.prototxt'
WEIGHT_VAE_DECODER_PATH = 'vae_decoder.onnx'
MODEL_VAE_DECODER_PATH = 'vae_decoder.onnx.prototxt'

REMOTE_PATH = 'https://storage.googleapis.com/ailia-models/anything_v3/'

SAVE_IMAGE_PATH = 'output.png'


# ======================
# Arguemnt Parser Config
# ======================
parser = get_base_parser(
    'Anything V3', None, SAVE_IMAGE_PATH
)
parser.add_argument(
    "-i", "--input", metavar="TEXT", type=str,
    default="pikachu",
    help="the prompt to render"
)
parser.add_argument(
    '--onnx',
    action='store_true',
    help='execute onnxruntime version.'
)
args = update_parser(parser, check_input_type=False)


# ======================
# Main functions
# ======================
def recognize_from_text(pipe):
    prompt = args.input if isinstance(args.input, str) else args.input[0]
    logger.info("prompt: %s" % prompt)

    output_dir = 'outputs'
    os.makedirs(output_dir, exist_ok=True)
    output_name = '{}_{}.png'.format(prompt.replace(" ", "-"), random.randint(10000, 99999))
    output_path = os.path.join(output_dir, output_name)

    logger.info('Start inference...')

    image = pipe(prompt).images[0]
    image.save(output_path)
    logger.info(f'saved at : {output_path}')

    logger.info('Script finished successfully.')


def main():
    check_and_download_models(WEIGHT_UNET_PATH, MODEL_UNET_PATH, REMOTE_PATH)
    check_and_download_models(WEIGHT_SAFETY_CHECKER_PATH, MODEL_SAFETY_CHECKER_PATH, REMOTE_PATH)
    check_and_download_models(WEIGHT_TEXT_ENCODER_PATH, MODEL_TEXT_ENCODER_PATH, REMOTE_PATH)
    check_and_download_models(WEIGHT_VAE_ENCODER_PATH, MODEL_VAE_ENCODER_PATH, REMOTE_PATH)
    check_and_download_models(WEIGHT_VAE_DECODER_PATH, MODEL_VAE_DECODER_PATH, REMOTE_PATH)

    if not os.path.exists(WEIGHT_PB_UNET_PATH):
        logger.info('Downloading weights.pb...')
        urlretrieve(REMOTE_PATH, WEIGHT_PB_UNET_PATH, progress_print)
    logger.info('weights.pb is prepared!')

    env_id = args.env_id

    # initialize
    if not args.onnx:
        logger.info("Ailia mode is not implemented.")
        exit()
    else:
        import transformers
        import df
        from df import OnnxRuntimeModel

        unet = OnnxRuntimeModel.from_pretrained(
            "./", "unet.onnx",
            {'provider': 'CPUExecutionProvider', 'sess_options': None}
        )
        safety_checker = OnnxRuntimeModel.from_pretrained(
            "./", "safety_checker.onnx",
            {'provider': 'CPUExecutionProvider', 'sess_options': None}
        )
        vae_decoder = OnnxRuntimeModel.from_pretrained(
            "./", "vae_decoder.onnx",
            {'provider': 'CPUExecutionProvider', 'sess_options': None}
        )
        pndm_scheduler = df.schedulers.scheduling_pndm.PNDMScheduler.from_pretrained(
            "./scheduler"
        )
        feature_extractor = transformers.CLIPImageProcessor.from_pretrained(
            "./feature_extractor"
        )
        text_encoder = OnnxRuntimeModel.from_pretrained(
            "./", "text_encoder.onnx",
            {'provider': 'CPUExecutionProvider', 'sess_options': None}
        )
        vae_encoder = OnnxRuntimeModel.from_pretrained(
            "./", "vae_encoder.onnx",
            {'provider': 'CPUExecutionProvider', 'sess_options': None}
        )
        tokenizer = transformers.CLIPTokenizer.from_pretrained(
            "./tokenizer"
        )

    # set pipeline
    use_transformers = True
    use_diffusers = False

    if use_diffusers and use_transformers:
        import diffusers
        pipeline_cls = diffusers.OnnxStableDiffusionPipeline
    elif not use_diffusers and use_transformers:
        pipeline_cls = df.OnnxStableDiffusionPipeline
    else:
        print('not implemented.')
        exit()
    
    pipe = pipeline_cls(
        vae_encoder = vae_encoder,
        vae_decoder = vae_decoder,
        text_encoder = text_encoder,
        tokenizer = tokenizer,
        unet = unet,
        scheduler = pndm_scheduler,
        safety_checker = safety_checker,
        feature_extractor = feature_extractor,
        requires_safety_checker = True       
    )

    # generate
    recognize_from_text(pipe)


if __name__ == '__main__':
    main()
