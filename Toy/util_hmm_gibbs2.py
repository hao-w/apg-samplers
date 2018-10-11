import math
import torch
from torch.distributions.dirichlet import Dirichlet
from torch.distributions.multivariate_normal import MultivariateNormal
from torch.distributions.one_hot_categorical import OneHotCategorical as cat
from torch.distributions.categorical import Categorical
from scipy.stats import invwishart
import numpy as np
import sys
sys.path.append('/home/hao/Research/probtorch/')
import probtorch
from probtorch.util import log_sum_exp
import time



def pirors(Y, T, D, K):
    ## set up prior
    alpha_init_0 = torch.ones(K)
    # L = torch.ones((K, K))  / (2 *(K-1))
    #alpha_trans_0 = torch.cat((torch.cat((torch.eye(4)*0.5, torch.ones((4, K-4)) * (0.5 / (K-4))), 1), torch.ones((K-4, K)) * (1.0 / K)), 0)
    # m_0 = torch.FloatTensor([[1, 1], [1, -1], [-1, -1], [-1, 1]]) * (1 / math.sqrt(2))
    alpha_trans_0 = torch.ones((K, K)) * (1/ K)
    m_0 = Y.mean(0).float()
    beta_0 = 1.0
    nu_0 = 6.0
    # W_0 =  (nu_0-D-1) * torch.mm((Y - Y.mean(0)).transpose(0,1), (Y - Y.mean(0))) / (T)
    W_0 =  torch.mm((Y - Y.mean(0)).transpose(0,1), (Y - Y.mean(0))) / (T * nu_0)
    return alpha_init_0, alpha_trans_0, m_0, beta_0, nu_0, W_0

def quad(a, B):
    return torch.mm(torch.mm(a.transpose(0, 1), B), a)
#
# def gibbs_local(Pi, A, mu_ks, cov_ks, Y, T, D, K):
#     Zs = torch.zeros(T)
#     for t in range(T):
#         if t == 0:
#             Pi_post = torch.zeros(K).float()
#             for k in range(K):
#                 Pi_post[k] = Categorical(Pi).log_prob(torch.Tensor([k])) + MultivariateNormal(mu_ks[k], cov_ks[k]).log_prob(Y[t])
#             Pi_post = torch.exp(Pi_post - log_sum_exp(Pi_post))
#             Zs[t] = Categorical(Pi_post).sample().item()
#         else:
#             pre = A[Zs[t].item()]
#             Pi_post = torch.zeros(K).float()
#             for k in range(K):
#             # zt_k_onehot = torch.zeros(K)
#             # zt_k_onehot[k] = 1
#                 Pi_post[k] = Categorical(pre).log_prob(torch.Tensor([k])) + MultivariateNormal(mu_ks[k], cov_ks[k]).log_prob(Y[t])
#             Pi_post = torch.exp(Pi_post - log_sum_exp(Pi_post))
#             Zs[t] = Categorical(Pi_post).sample().item()
#     return Zs.int()

def gibbs_local(Pi, mu_ks, cov_ks, Y, T, D, K):
    Zs = torch.zeros((T, K))
    for t in range(T):
        Pi_post = torch.zeros(K).float()
        for k in range(K):
            # zt_k_onehot = torch.zeros(K)
            # zt_k_onehot[k] = 1
            Pi_post[k] = Categorical(Pi).log_prob(torch.Tensor([k])) + MultivariateNormal(mu_ks[k], cov_ks[k]).log_prob(Y[t])
        Pi_post = torch.exp(Pi_post - log_sum_exp(Pi_post))
        Zs[t] = cat(Pi_post).sample()
    return Zs


def stats(Zs, Y, D, K):
    N_ks = Zs.sum(0)
    Y_ks = torch.zeros((K, D))
    S_ks = torch.zeros((K, D, D))

    Zs_expanded = Zs.repeat(D, 1, 1)
    for k in range(K):
        Y_ks[k] = torch.mul(Zs_expanded[:, :, k].transpose(0,1), Y).sum(0) / N_ks[k]
        Zs_expanded2 = Zs_expanded[:, :, k].repeat(D, 1, 1).permute(2, 1, 0)
        Y_diff = Y - Y_ks[k]
        Y_bmm = torch.bmm(Y_diff.unsqueeze(2), Y_diff.unsqueeze(1))
        S_ks[k] = torch.mul(Zs_expanded2, Y_bmm).sum(0) / (N_ks[k])
    return N_ks, Y_ks, S_ks


# def stats2(Zs, Y, T, D, K):
#     # N_ks = torch.zeros(K)
#     N_ks = Zs.sum(0)
#     Y_ks = torch.zeros((K, D))
#     S_ks = torch.zeros((K, D, D))
#
#     decode_onehot = torch.arange(K).repeat(T, 1).float()
#     labels = torch.bmm(decode_onehot.unsqueeze(1), Zs.unsqueeze(2)).squeeze(-1).squeeze(-1).int()
#     for k in range(K):
#
#         for t in range(T):
#             if labels[t].item() == k:
#                 Y_ks[k] += Y[t]
#         Y_ks[k] /= N_ks[k]
#         Y_diff = Y - Y_ks[k]
#         Y_bmm = torch.bmm(Y_diff.unsqueeze(2), Y_diff.unsqueeze(1))
#         for t in range(T):
#             if labels[t].item() == k:
#                 S_ks[k] += Y_bmm[t]
#         S_ks[k] /= N_ks[k]
#     return N_ks, Y_ks, S_ks

def pairwise(Zs, T):
    return torch.bmm((Zs[:T].unsqueeze(-1), Zs[1:].unsqueeze(1)))

def gibbs_global(Zs, alpha_init_0, nu_0, W_0, m_0, beta_0, N_ks, Y_ks, S_ks, T, D, K):
    ## Zs is N * K tensor where each row is one-hot encoding of a sample of latent state
    ## sample /pi
    alpha_init_hat = alpha_init_0 + N_ks
    # for k in range(K):
    #     alpha_init_hat[k] += list(Zs.data.numpy()).count(k)
    Pi = Dirichlet(alpha_init_hat).sample()
    ## sample A
    # alpha_trans_hat = alpha_trans_0

    # A = torch.zeros((K, K)).float()
    # for k in range(K):
    # # for k in range(K):
    #    A[k] = Dirichlet(alpha_trans_hat[k]).sample()
    # sample mu_k and Sigma_k
    nu_ks = nu_0 + N_ks
    beta_ks = beta_0 + N_ks
    m_ks = torch.zeros((K, D))
    W_ks = torch.zeros((K, D, D))
    cov_ks = torch.zeros((K, D, D))
    mu_ks = torch.zeros((K, D))
    for k in range(K):
        m_ks[k] = (beta_0 * m_0 + N_ks[k] * Y_ks[k]) / beta_ks[k]
        temp2 = (Y_ks[k] - m_0).view(D, 1)
        W_ks[k] = W_0 + N_ks[k] * S_ks[k] + (beta_0*N_ks[k] / (beta_0 + N_ks[k])) * torch.mm(temp2, temp2.transpose(0, 1))
        ## sample mu_k and Sigma_k from posterior
        cov_ks[k] = torch.from_numpy(invwishart.rvs(df=nu_ks[k].item(), scale=W_ks[k].data.numpy()))
        mu_ks[k] = MultivariateNormal(loc=m_ks[k], covariance_matrix=cov_ks[k] / beta_ks[k].item()).sample()
    return Pi, mu_ks, cov_ks

def log_joint(alpha_init_0, nu_0, W_0, m_0, beta_0, Zs, Pi, mu_ks, cov_ks, Y, T, D, K):
    log_joint_prob = 0.0
    ## some vectorization to pick up the k-th global  for each state by one hot encoding
    decode_onehot = torch.arange(K).repeat(T, 1).float()
    labels = torch.bmm(decode_onehot.unsqueeze(1), Zs.unsqueeze(2)).squeeze(-1).squeeze(-1).int()
    # Y_ll_means = torch.bmm(Zs.unsqueeze(1), mu_ks.repeat(T, 1, 1)).squeeze(1)
    # Y_ll_covs = torch.mul(Zs.transpose(0,1).repeat(D, D, 1, 1).permute(-1, 2, 1, 0),  cov_ks.repeat(T, 1, 1, 1)).squeeze(1)
    # Ais = torch.bmm(Zs[:T].unsqueeze(1), A.repeat(T-1, 1, 1)).squeeze(1)
    ## start compute LL
    for t in range(T):
        log_joint_prob += MultivariateNormal(mu_ks[labels[t].item()], cov_ks[labels[t].item()]).log_prob(Y[t]) # likelihood of obs
        log_joint_prob += cat(Pi).log_prob(Zs[t]) # z_1 | pi
        # if t == 0:
        #     y_joint_prob += cat(pi).log_prob(Zs[t]) # z_1 | pi
        # else:
        #     y_joint_prob += cat(Ais[t-1]).log_prob(Zs[t]) # z_t | z_t-1 = j*, A
    log_joint_prob += Dirichlet(alpha_init_0).log_prob(Pi)
    for k in range(K):
        # y_joint_prob += Dirichlet(alpha_init_0[k]).log_prob(A[k]) ## prior of A
        log_joint_prob += MultivariateNormal(m_0, cov_ks[k] / beta_0).log_prob(mu_ks[k])# prior of mu_ks
        log_joint_prob += invwishart.logpdf(cov_ks[k].data.numpy(), nu_0, W_0.data.numpy())# prior of cov_ks
    return log_joint_prob