from collections import namedtuple

import torch
from .observation_type import ObservationType
import torch.nn.functional as F
import torch.nn.intrinsic as nni
import torch.nn.intrinsic.qat as nniqat
import torch.nn.qat as nnqat
import torch.nn.quantized._reference as nnqr

from ...fuser_method_mappings import reverse_sequential_wrapper2

weighted_op_int8_dtype_config = {
    # optional, input activation dtype
    "input_dtype": torch.quint8,
    # optional, weight dtype
    "weight_dtype": torch.qint8,
    # optional, bias dtype
    "bias_dtype": torch.float,
    # optional, output activation dtype
    "output_dtype": torch.quint8
}

_ConvMetadata = namedtuple("_ConvMetadata", ["root", "reference", "qat", "relu", "relu_qat", "bn_qat", "bn_relu_qat", "func"])
_Conv1dMetadata = _ConvMetadata(torch.nn.Conv1d, nnqr.Conv1d, nnqat.Conv1d, nni.ConvReLU1d,
                                nniqat.ConvReLU1d, nniqat.ConvBn1d, nniqat.ConvBnReLU1d, F.conv1d)
_Conv2dMetadata = _ConvMetadata(torch.nn.Conv2d, nnqr.Conv2d, nnqat.Conv2d, nni.ConvReLU2d,
                                nniqat.ConvReLU2d, nniqat.ConvBn2d, nniqat.ConvBnReLU2d, F.conv2d)
_Conv3dMetadata = _ConvMetadata(torch.nn.Conv3d, nnqr.Conv3d, nnqat.Conv3d, nni.ConvReLU3d,
                                nniqat.ConvReLU3d, nniqat.ConvBn3d, nniqat.ConvBnReLU3d, F.conv3d)

def _get_linear_configs():
    """
    Return all configs related to linear modules and ops.
    """
    observation_type = ObservationType.OUTPUT_USE_DIFFERENT_OBSERVER_AS_INPUT
    dtype_configs = [weighted_op_int8_dtype_config]
    linear_configs = []

    # linear module
    linear_configs.append({
        # Please see README under this folder for pattern format
        "pattern": torch.nn.Linear,
        "observation_type": observation_type,
        "dtype_configs": dtype_configs,
        # the root module for the pattern, used to query the reference quantized module
        # e.g. for a (torch.nn.ReLU, torch.nn.Linear) pattern, the root will be torch.nn.Linear
        "root_module": torch.nn.Linear,
        # the corresponding reference quantized module for the root module
        "reference_quantized_module_for_root": nnqr.Linear,
        "qat_module": nnqat.Linear,
    })        
    # linear qat module
    linear_configs.append({
        "pattern": nnqat.Linear,
        "observation_type": observation_type,
        "dtype_configs": dtype_configs,
        "root_module": torch.nn.Linear,
        "reference_quantized_module_for_root": nnqr.Linear,
    })
    # functional linear
    linear_configs.append({
        "pattern": torch.nn.functional.linear,
        "observation_type": observation_type,
        "dtype_configs": dtype_configs,
    })
    # linear relu, fused module
    linear_configs.append({
        "pattern": nni.LinearReLU,
        "observation_type": observation_type,
        "dtype_configs": dtype_configs ,
        "root_module": torch.nn.Linear,
        "reference_quantized_module_for_root": nnqr.Linear,
        "qat_module": nniqat.LinearReLU,
    })
    # linear relu, qat fused module
    linear_configs.append({
        "pattern": nniqat.LinearReLU,
        "observation_type": observation_type,
        "dtype_configs": dtype_configs,
        "root_module": torch.nn.Linear,
        "reference_quantized_module_for_root": nnqr.Linear,
    })
    # linear relu, linear module + relu module
    linear_configs.append({
        "pattern": (torch.nn.ReLU, torch.nn.Linear),
        "observation_type": observation_type,
        "dtype_configs": dtype_configs, 
        "fuser_method": reverse_sequential_wrapper2(nni.LinearReLU),
    })
    # linear relu, linear module + functional relu
    linear_configs.append({
        "pattern": (F.relu, torch.nn.Linear),
        "observation_type": observation_type,
        "dtype_configs": dtype_configs,
        "fuser_method": reverse_sequential_wrapper2(nni.LinearReLU),
    })
    # linear relu, functional linear + relu module
    linear_configs.append({
        "pattern": (torch.nn.ReLU, F.linear),
        "observation_type": observation_type,
        "dtype_configs": dtype_configs,
    })
    # linear relu, functional linear + functional relu
    linear_configs.append({
        "pattern": (F.relu, F.linear),
        "observation_type": observation_type,
        "dtype_configs": dtype_configs,
    })
    # linear bn, fused module
    linear_configs.append({
        "pattern": nni.LinearBn1d,
        "observation_type": observation_type,
        "dtype_configs": dtype_configs,
        "root_module": torch.nn.Linear,
        "reference_quantized_module_for_root": nnqr.Linear,
        "qat_module": nniqat.LinearBn1d,
    })
    # linear bn, qat fused module
    linear_configs.append({
        "pattern": nniqat.LinearBn1d,
        "observation_type": observation_type,
        "dtype_configs": dtype_configs, 
        "root_module": torch.nn.Linear,
        "reference_quantized_module_for_root": nnqr.Linear,
    })
    return linear_configs

def _get_conv_configs():
    """
    Return all configs related to conv modules and ops.
    """
    conv_configs = []
    observation_type = ObservationType.OUTPUT_USE_DIFFERENT_OBSERVER_AS_INPUT
    dtype_configs = [weighted_op_int8_dtype_config]
    for convs in [_Conv1dMetadata, _Conv2dMetadata, _Conv3dMetadata]:
        # conv module
        conv_configs.append({
            "pattern": convs.root,
            "observation_type": observation_type,
            "dtype_configs": dtype_configs,
            "root_module": convs.root,
            "reference_quantized_module_for_root": convs.reference,
            "qat_module": convs.qat,
        })
        # conv qat module
        conv_configs.append({
            "pattern": convs.qat,
            "observation_type": observation_type,
            "dtype_configs": dtype_configs,
            "root_module": convs.root,
            "reference_quantized_module_for_root": convs.reference,
        })
        # functional conv
        conv_configs.append({
            "pattern": convs.func,
            "observation_type": observation_type,
            "dtype_configs": dtype_configs,
        })
        # conv relu, fused module
        conv_configs.append({
            "pattern": convs.relu,
            "observation_type": observation_type,
            "dtype_configs": dtype_configs,
            "root_module": convs.root,
            "reference_quantized_module_for_root": convs.reference,
            "qat_module": nniqat.ConvReLU1d,
        })
        # conv relu, qat fused module
        conv_configs.append({
            "pattern": convs.relu_qat,
            "observation_type": observation_type,
            "dtype_configs": dtype_configs,
            "root_module": convs.root,
            "reference_quantized_module_for_root": convs.reference,
        })
        # conv relu, functional conv + relu module
        conv_configs.append({
            "pattern": (torch.nn.ReLU, convs.func),
            "observation_type": observation_type,
            "dtype_configs": dtype_configs,
        })
        # conv relu, functional conv + functional relu
        conv_configs.append({
            "pattern": (F.relu, convs.func),
            "observation_type": observation_type,
            "dtype_configs": dtype_configs,
        })
        # conv bn, qat fused module
        conv_configs.append({
            "pattern": convs.bn_qat,
            "observation_type": observation_type,
            "dtype_configs": dtype_configs,
            "root_module": convs.root,
            "reference_quantized_module_for_root": convs.reference,
        })
        # conv bn relu, qat fused module
        conv_configs.append({
            "pattern": convs.bn_relu_qat,
            "observation_type": observation_type,
            "dtype_configs": dtype_configs, 
            "root_module": convs.root,
            "reference_quantized_module_for_root": convs.reference,
        })
    return conv_configs

def get_native_backend_config_dict():
    """ Get backend for PyTorch Native backend_config_dict (fbgemm/qnnpack). """
    return {
        # optional
        "name": "native",
        "configs": [
            *_get_linear_configs(),
            *_get_conv_configs(),
        ],
    }
