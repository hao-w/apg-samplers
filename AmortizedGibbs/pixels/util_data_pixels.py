import torch
import numpy as np
import matplotlib.pyplot as plt
from bokeh.plotting import figure, output_notebook, show
from bokeh.models import Range1d
from bokeh.io import push_notebook, show, output_notebook
from scipy.stats import multivariate_normal as mvn
import time

def step(state, box_bound, mu_ks):
    xy_new = state[ :2] + mvn.rvs(mean=state[2: ], cov=mu_ks)
    while(True):
        if xy_new[0] < box_bound[0]:
            x_over = abs(box_bound[0] - xy_new[0])
            xy_new[0] = box_bound[0] + x_over
            state[2] *= -1
        elif xy_new[0] > box_bound[1]:
            x_over = abs(box_bound[1] - xy_new[0])
            xy_new[0] = box_bound[1] - x_over
            state[2] *= -1
        elif xy_new[1] < box_bound[2]:
            y_over = abs(box_bound[2] - xy_new[1])
            xy_new[1] = box_bound[2] + y_over
            state[3] *= -1
        elif xy_new[1] > box_bound[3]:
            y_over = abs(box_bound[3] - xy_new[1])
            xy_new[1] = box_bound[3] - y_over
            state[3] *= -1
        else:
            state[:2] = xy_new
            break
    return state

def compute_state(velocity):
    if velocity[0] > 0 and velocity[1] > 0:
        return 0
    if velocity[0] > 0 and velocity[1] < 0:
        return 1
    if velocity[0] < 0 and velocity[1] < 0:
        return 2
    if velocity[0] < 0 and velocity[1] > 0:
        return 3

def init_velocity(dt):
    init_v = np.random.random(2) * np.random.choice([-1,1], size=2)
    v_norm = ((init_v ** 2 ).sum()) ** 0.5 ## compute norm for each initial velocity
    init_v = init_v / v_norm * dt ## to make the velocity lying on a circle
    return init_v

def intialization(init_v, Boundary):
    init_state = np.zeros(4)
    init_state[0] = Boundary * np.random.random() * np.random.choice([-1,1])
    init_state[1] = Boundary * np.random.random() * np.random.choice([-1,1])

    init_state[2:] = init_v
    return init_state

def generate_seq(T, dt, Boundary, init_v, noise_cov, radius):
    A = np.zeros((4,4))
    STATE = np.zeros((T+1, 4)) # since I want to make the displacement of length T, I need the coordinates of length T+1
    init_state = intialization(init_v, Boundary - radius*2)
    box_bound = np.array([-1, 1, -1, 1]) * (Boundary-radius*2)
    Zs = np.zeros((T, 4))
    STATE[0] = init_state
    for i in range(T):
        state = step(STATE[i], box_bound, noise_cov)
        STATE[i+1] = state
        new_state = compute_state(state[2:])
        Zs[i, new_state] = 1
        if i != 0:
            A[old_state, new_state] += 1
        old_state = new_state
    Disp = (STATE[1:] - STATE[:T])[:, :2]

    np.place(A, A==0, 1 / T)
    A_sum = A.sum(1)
    A = A / A_sum[:, None]
    Zs = np.array(Zs)
    return STATE, Disp, A, Zs

def generate_seq_T(T, K, dt, Boundary, init_v, noise_cov, radius):
    STATE, Disp, A_true, Zs_true = generate_seq(T, dt, Boundary, init_v, noise_cov, radius)
    ## true global variables
    cov_true = np.tile(noise_cov, (K, 1, 1))
    dirs = np.array([[1, 1], [1, -1], [-1, -1], [-1, 1]])
    mu_true = np.tile(np.absolute(init_v), (K, 1)) * dirs
    Pi_true = np.ones(K) * (1/K)
    cov_ks = torch.from_numpy(cov_true).float()
    mu_ks = torch.from_numpy(mu_true).float()
    Pi = torch.from_numpy(Pi_true).float()
    Y = torch.from_numpy(Disp).float()
    return STATE, mu_ks, cov_ks, Pi, Y, A_true, Zs_true

def generate_frames(STATE, Boundary, pixels, dpi, radius, seq_ind):
    length_states = STATE.shape[0]
    for s in range(length_states):
        fig = plt.figure(frameon=False)
        fig.set_size_inches(pixels/dpi, pixels/dpi)
        ax = plt.Axes(fig, [0 , 0 , 1, 1])
        ax.set_axis_off()
        fig.add_axes(ax)
        ball = plt.Circle((STATE[s, 0], STATE[s, 1]), radius, color='black')
        ax.set_xlim((-Boundary, Boundary))
        ax.set_ylim((-Boundary, Boundary))
        ax.add_artist(ball)
        plt.savefig('images_test/%s-%s.png' % (str(seq_ind), str(s)),dpi=dpi)
        plt.close()

def generate_pixels(T, num_seq, Boundary, dt, noise_ratio, pixels, dpi, radius):
    init_v = init_velocity(dt)
    for s in range(num_seq):
        STATE, Disp, A, Zs = generate_seq(T, dt, Boundary, init_v, noise_cov, radius)
        generate_frames(STATE, Boundary, pixels, dpi, radius, s)
    print('dataset generate completed!')
