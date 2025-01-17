import matplotlib.pyplot as plt
from netshare.utils import OutputType, Output, Normalization
import numpy as np
import matplotlib

matplotlib.use("Agg")


def renormalize_per_sample(
    data_feature,
    data_attribute,
    data_feature_outputs,
    data_attribute_outputs,
    gen_flags,
    num_real_attribute,
):
    attr_dim = 0
    for i in range(num_real_attribute):
        attr_dim += data_attribute_outputs[i].dim
    attr_dim_cp = attr_dim

    fea_dim = 0
    for output in data_feature_outputs:
        if output.type_ == OutputType.CONTINUOUS:
            for _ in range(output.dim):
                max_plus_min_d_2 = data_attribute[:, attr_dim]
                max_minus_min_d_2 = data_attribute[:, attr_dim + 1]
                attr_dim += 2

                max_ = max_plus_min_d_2 + max_minus_min_d_2
                min_ = max_plus_min_d_2 - max_minus_min_d_2

                max_ = np.expand_dims(max_, axis=1)
                min_ = np.expand_dims(min_, axis=1)

                if output.normalization == Normalization.MINUSONE_ONE:
                    data_feature[:, :, fea_dim] = (
                        data_feature[:, :, fea_dim] + 1.0
                    ) / 2.0

                data_feature[:, :, fea_dim] = (
                    data_feature[:, :, fea_dim] * (max_ - min_) + min_
                )

                fea_dim += 1
        else:
            fea_dim += output.dim

    tmp_gen_flags = np.expand_dims(gen_flags, axis=2)
    data_feature = data_feature * tmp_gen_flags

    data_attribute = data_attribute[:, 0:attr_dim_cp]

    return data_feature, data_attribute


def normalize_per_sample(
        data_feature, data_attribute, data_feature_outputs,
        data_attribute_outputs, eps=1e-4):
    # assume all samples have maximum length
    data_feature_min = np.amin(data_feature, axis=1)
    data_feature_max = np.amax(data_feature, axis=1)

    additional_attribute = []
    additional_attribute_outputs = []

    dim = 0
    for output in data_feature_outputs:
        if output.type_ == OutputType.CONTINUOUS:
            for _ in range(output.dim):
                max_ = data_feature_max[:, dim] + eps
                min_ = data_feature_min[:, dim] - eps

                additional_attribute.append((max_ + min_) / 2.0)
                additional_attribute.append((max_ - min_) / 2.0)
                additional_attribute_outputs.append(
                    Output(
                        type_=OutputType.CONTINUOUS,
                        dim=1,
                        normalization=output.normalization,
                        is_gen_flag=False,
                    )
                )
                additional_attribute_outputs.append(
                    Output(
                        type_=OutputType.CONTINUOUS,
                        dim=1,
                        normalization=Normalization.ZERO_ONE,
                        is_gen_flag=False,
                    )
                )

                max_ = np.expand_dims(max_, axis=1)
                min_ = np.expand_dims(min_, axis=1)

                data_feature[:, :, dim] = (data_feature[:, :, dim] - min_) / (
                    max_ - min_
                )
                if output.normalization == Normalization.MINUSONE_ONE:
                    data_feature[:, :, dim] = data_feature[:,
                                                           :, dim] * 2.0 - 1.0

                dim += 1
        else:
            dim += output.dim

    real_attribute_mask = [True] * len(data_attribute_outputs) + [False] * len(
        additional_attribute_outputs
    )

    additional_attribute = np.stack(additional_attribute, axis=1)
    data_attribute = np.concatenate(
        [data_attribute, additional_attribute], axis=1)
    data_attribute_outputs.extend(additional_attribute_outputs)

    return data_feature, data_attribute, data_attribute_outputs, real_attribute_mask


def add_gen_flag(data_feature, data_gen_flag, data_feature_outputs, sample_len):
    for output in data_feature_outputs:
        if output.is_gen_flag:
            raise Exception(
                "is_gen_flag should be False for all"
                "feature_outputs")

    if data_feature.shape[2] != np.sum([t.dim for t in data_feature_outputs]):
        raise Exception("feature dimension does not match feature_outputs")

    if len(data_gen_flag.shape) != 2:
        raise Exception("data_gen_flag should be 2 dimension")

    num_sample, length = data_gen_flag.shape

    data_gen_flag = np.expand_dims(data_gen_flag, 2)

    data_feature_outputs.append(
        Output(type_=OutputType.DISCRETE, dim=2, is_gen_flag=True)
    )

    shift_gen_flag = np.concatenate(
        [data_gen_flag[:, 1:, :], np.zeros((data_gen_flag.shape[0], 1, 1))], axis=1
    )
    if length % sample_len != 0:
        raise Exception("length must be a multiple of sample_len")
    data_feature = np.concatenate(
        [data_feature, shift_gen_flag, (1 - shift_gen_flag)], axis=2
    )

    return data_feature, data_feature_outputs
