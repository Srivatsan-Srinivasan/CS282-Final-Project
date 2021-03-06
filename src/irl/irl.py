import numpy as np
import numba as nb
import pandas as np
import itertools
import multiprocessing as mp

from constants import *
from utils.utils import is_terminal_state, compute_terminal_state_reward


def make_initial_state_sampler(df, has_priority=True):
    '''
    we only care about empirically observed initial states.
    '''
    if has_priority:
        probs = df[df['bloc'] == 1]['state'].value_counts(normalize=True).tolist()
        f = lambda : np.random.choice(np.arange(len(probs)), p=probs)
    else:
        initial_states = df[df['bloc'] == 1]['state'].unique().tolist()
        f = lambda : np.random.choice(initial_states)
    return f

def get_initial_state_distribution(df):
    '''
    we only care about empirically observed initial states.
    '''
    probs = df[df['bloc'] == 1]['state'].value_counts(normalize=True).tolist()
    return probs


def make_state_centroid_finder(df, columns=None):
    if columns is not None:
        df = df[columns]
    def f(state):
        return df.iloc[state]
    return f


def sample_state(probs):
    return np.random.choice(np.arange(len(probs)), p=probs)

def estimate_feature_expectation(transition_matrix,
                                 initial_state_probs,
                                 phi,
                                 pi,
                                 num_trajectories=300,
                                 gamma=0.99,
                                 max_iter=1000):
    '''
    estimate mu_pi and v_pi with monte carlo simulation
    '''

    s = sample_state(initial_state_probs)
    mu = np.zeros((phi.shape[1]))
    v_sum = 0.0

    mus = []
    vs = []
    for i in range(num_trajectories):
        s = sample_state(initial_state_probs)
        for t in itertools.count():
            if t > max_iter:
                print('max iter timeout broke')
                break
            # accumulate phi(s) over trajectories
            mu += gamma**t * phi[s, :]
            chosen_a = pi.choose_action(s)
            probs = np.copy(transition_matrix[s, chosen_a, :])
            # need to renomralize so sum(probs) < 1
            probs /= np.sum(probs)
            new_s = np.random.choice(np.arange(len(probs)), p=probs)

            if is_terminal_state(new_s):
                # there's no phi(terminal_state)
                # in practice, non-zero rewars for terminal states
                num_features = mu.shape[0]
                v_sum += gamma** t * compute_terminal_state_reward(new_s, num_features)
                break
            s = new_s

    mu = mu / num_trajectories
    # let's not use v estimated here
    # let's use evaluate_policy_monte_carlo
    v =  v_sum / num_trajectories
    return mu, v


def make_phi(df_centroids):
    '''
    don't use this
    '''
    # median values for each centroid
    stats = df_centroids.describe()
    #take median
    median_state = stats.loc['50%']
    def phi(state):
        '''
        state: centroid values whose dimension is {num_features}
        phi: must apply decision rule (=indicator function)

        returs: binary matrix of R^{num_features}
        '''
        # TODO: implement this
        phi_s = np.array((state > median_state).astype(np.int))
        return phi_s
    return phi


def phi(df_centroids):
    # median values for each centroid
    stats = df_centroids.describe()
    #take median
    quartile_1 = stats.loc['25%']
    quartile_2 = stats.loc['50%']
    quartile_3 = stats.loc['75%']
    def phi(state):
        '''
        state: centroid values whose dimension is {num_features}
        phi: must apply decision rule (=indicator function)

        returs: binary matrix of R^{num_features}
        '''
        # TODO: implement this
        phi_s = np.array((state > median_state).astype(np.int))
        return phi_s
    return phi

def make_reward_computer(W, phi):
    def compute_reward(state):
        if is_terminal_state(state):
            # special case of terminal states
            # either 1 or -1
            num_features = W.shape[0]
            return compute_terminal_state_reward(state, num_features)
        return np.dot(W, phi[state, :])
    return compute_reward

def estimate_v_pi_tilda(W, mu, initial_state_probs, sample_size=100):
    # this does not work. don't use this for now.
    v_pi_tilda = np.dot(W, mu)
    # remove two terminal_states
    v_pi_tilda = v_pi_tilda[:v_pi_tilda.shape[0] - NUM_TERMINAL_STATES]
    v_pi_tilda_est = 0.0
    # TODO: vectorize this
    for _ in range(sample_size):
        s_0 = sample_state(initial_state_probs)
        v_pi_tilda_est += v_pi_tilda[s_0]
    return v_pi_tilda_est / sample_size
