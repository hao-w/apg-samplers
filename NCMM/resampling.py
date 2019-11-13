import torch
from torch.distributions.categorical import Categorical
"""
=========
TODO : provide more sampling methods like systematic resampling based on the paper:
GPU acceleration of the particle filter: the Metropolis resampler https://arxiv.org/abs/1202.6163
=========
"""
def resample(var, weights, dim_expand=True):
    dim1, dim2, dim3, dim4 = var.shape
    if dim_expand:
        if dim2 == 1:
            ancesters = Categorical(weights.permute(1, 2, 0).squeeze(0)).sample((dim1, )).unsqueeze(1).unsqueeze(-1).repeat(1, 1, 1, dim4)
        else:
            ancesters = Categorical(weights.permute(1, 2, 0)).sample((dim1, )).unsqueeze(-1).repeat(1, 1, 1, dim4)
    else:
        ancesters = Categorical(weights.transpose(0, 1)).sample((dim1, )).unsqueeze(-1).unsqueeze(-1).repeat(1, 1, dim3, dim4) ## S * B * N * K
    return torch.gather(var, 0, ancesters)

def sample_ancestral_index(weights, DEVICE):
    batch_size, num_particles = weights.size()
    indices = np.zeros([batch_size, num_particles])

    uniforms = np.random.uniform(size=[batch_size, 1])
    pos = (uniforms + np.arange(0, num_particles)) / num_particles

    normalized_weights = weights.cpu().data.numpy()

    # np.ndarray [batch_size, num_particles]
    cumulative_weights = np.cumsum(normalized_weights, axis=1)

    # hack to prevent numerical issues
    cumulative_weights = cumulative_weights / np.max(
        cumulative_weights, axis=1, keepdims=True)
    for batch in range(batch_size):
        indices[batch] = np.digitize(pos[batch], cumulative_weights[batch])
    return torch.from_numpy(indices).long().cuda().to(DEVICE)


def S_Resample(var, weights, DEVICE, idw_flag=True):
    S, B, dim3, dim4 = var.shape
    if idw_flag :
        indices = sample_ancestral_index(weights.view(S, B*dim3).transpose(0,1), DEVICE)
        ancesters = indices.transpose(0,1).view(S, B, dim3).unsqueeze(-1).repeat(1, 1, 1, dim4)
    else:
        indices = sample_ancestral_index(weights.transpose(0,1), DEVICE) # B * S or B * S * N
        ancesters = indices.transpose(0,1).unsqueeze(-1).unsqueeze(-1).repeat(1, 1, dim3, dim4)
    return torch.gather(var, 0, ancesters)
