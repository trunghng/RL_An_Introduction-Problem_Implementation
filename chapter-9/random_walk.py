import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm


class RandomWalk:
    '''
    Random walk with a transition radius
    '''


    def __init__(self, n_states, start_state, transition_radius):
        self.n_states = n_states
        self.start_state = start_state
        self.transition_radius = transition_radius
        self.states = np.arange(1, n_states + 1)
        self.end_states = [0, n_states + 1]
        self.actions = [-1, 1]
        self.rewards = [-1, 0, 1]


    def is_terminal(self, state):
        '''
        Whether state @state is an end state

        Params
        ------
        state: int
            current state
        '''
        return state in self.end_states


    def get_pos_next_states(self, state, action):
        '''
        Get possible states at state @state, taking action @action

        Params
        ------
        state: int
            current state
        action: int
            action take

        Return
        ------
        pos_next_states: np.ndarray
            list of possible next states
        '''
        if action == self.actions[0]:
            pos_next_states = np.arange(max(self.end_states[0], state - 
                self.transition_radius), state + action + 1)
        else:
            pos_next_states = np.arange(state + action, min(self.end_states[1], 
                state + self.transition_radius) + 1)

        return pos_next_states


    def get_state_transition(self, state, pos_next_states):
        '''
        Get state transition at state @state

        Params
        ------
        state: int
            current state
        pos_next_states: np.ndarray
            list of possible next states

        Return
        ------
        state_transition: np.ndarray
            state transition probability
        '''
        next_state_prob = 1.0 / self.transition_radius
        state_transition = np.array([next_state_prob for _ in pos_next_states])

        if self.end_states[0] == pos_next_states[0]:
            state_transition[0] += (self.transition_radius 
                - len(pos_next_states)) * next_state_prob
        elif self.end_states[1] == pos_next_states[-1]:
            state_transition[-1] += (self.transition_radius 
                - len(pos_next_states)) * next_state_prob

        return state_transition


    def get_next_state(self, state, action):
        '''
        Get the next state from possible next states

        Params
        ------
        pos_next_state: np.ndarray
            list of possible next states

        Return
        ------
        next_state: int
            next state
        '''
        pos_next_states = self.get_pos_next_states(state, action)
        state_transition = self.get_state_transition(state, pos_next_states)

        next_state = np.random.choice(pos_next_states, p=state_transition)

        return next_state


    def get_reward(self, state):
        '''
        Get reward when ending at state @state

        Params
        ------
        state: int
            current state

        Return
        ------
        reward: int
            reward at state @state
        '''
        if state == self.end_states[0]:
            reward = self.rewards[0]
        elif state == self.end_states[1]:
            reward = self.rewards[2]
        else:
            reward = self.rewards[1]

        return reward


    def take_action(self, state, action):
        '''
        Take action @action at state @state

        Params
        ------
        state: int
            current state
        action: int
            action taken

        Return
        ------
        (next_state, reward): (int, int)
            a tuple of next state and reward
        '''
        next_state = self.get_next_state(state, action)
        reward = self.get_reward(next_state)

        return next_state, reward


def get_true_value(random_walk):
    '''
    Calculate true values of @random_walk by DP

    Params
    ------
    random_walk: RandomWalk
        random walk env

    Return
    ------
    true_value: np.ndarray
        true values of @random_walk's states
    '''
    # With this random walk, it makes sense to initialize the values in the closed interval 
    # [-1, 1] and increasing
    n_states = random_walk.n_states
    true_value = np.arange(-(n_states + 1), n_states + 3, 2) / (n_states + 1)
    theta = 1e-2

    while True:
        old_value = true_value.copy()
        for idx_state, state in enumerate(random_walk.states):
            true_value[state] = 0

            for idx_action, action in enumerate(random_walk.actions):
                pos_next_states = random_walk.get_pos_next_states(state, action)
                state_transition = random_walk.get_state_transition(state, pos_next_states)

                for i, next_state in enumerate(pos_next_states):
                    trans_prob = state_transition[i]
                    true_value[state] += 0.5 * trans_prob * true_value[next_state]

        delta = np.sum(np.abs(old_value - true_value))
        if delta < theta:
            break

    true_value[0] = true_value[-1] = 0

    return true_value


def random_policy(random_walk):
    return np.random.choice(random_walk.actions)


class StateAggregation:
    '''
    State Aggregation
    '''

    def __init__(self, n_groups, n_states):
        self.n_groups = n_groups
        self.group_size = n_states // n_groups
        self.w = np.zeros(n_groups)


    def get_group(self, state):
        '''
        Get group index

        Params
        ------
        state: int
            current state

        Return
        ------
        group_idx: int
            group index
        '''
        group_idx = int((state - 1) // self.group_size)
        return group_idx


    def get_grad(self, state):
        '''
        Compute the gradient w.r.t @self.w at state @state

        Params
        ------
        state: int
            current state

        Return
        ------
        grad: np.ndarray
            gradient w.r.t @self.w at the current state
        '''
        group_idx = self.get_group(state)
        grad = np.zeros(self.n_groups)
        grad[group_idx] = 1
        return grad


    def get_value(self, state, random_walk):
        '''
        Get value function at state @state
        States within a group share the same value function, which is a component of w

        Params
        ------
        state: int
            current state
        random_walk: RandomWalk
            random walk

        Return
        ------
        value_func: float
            value function at state @state
        '''
        if random_walk.is_terminal(state):
            value_func = 0
        else:
            group_idx = self.get_group(state)
            value_func = self.w[group_idx]
        return value_func


def gradient_mc_state_aggregation(state_agg, random_walk, alpha, mu):
    '''
    Gradient Monte Carlo with state aggregation

    Params
    ------
    state_agg: StateAggregation
    random_walk: RandomWalk
        random walk env
    alpha: float
        step size
    mu: np.ndarray
        state distribution
    '''
    state = random_walk.start_state
    trajectory = [state]

    while not random_walk.is_terminal(state):
        action = random_policy(random_walk)
        next_state = random_walk.get_next_state(state, action)
        trajectory.append(next_state)
        state = next_state
    reward = random_walk.get_reward(state)

    # since reward at every states except terminal ones is 0, and discount factor gamma = 1,
    # the return at each state is equal to the reward at the terminal state.
    for state in trajectory[:-1]:
        state_agg.w += alpha * (reward - 
            state_agg.get_value(state, random_walk)) * state_agg.get_grad(state)
        mu[state] += 1


def gradient_mc_state_aggregation_plot(random_walk, true_value):
    '''
    Plotting gradient MC w/ state aggregation
    '''
    alpha = 2e-5
    n_groups = 10
    n_eps = 100000
    mu = np.zeros(n_states + 2)
    state_agg = StateAggregation(n_groups, random_walk.n_states)

    for _ in tqdm(range(n_eps)):
        gradient_mc_state_aggregation(state_agg, random_walk, alpha, mu)

    mu /= np.sum(mu)
    value_funcs = [state_agg.get_value(state, random_walk)
        for state in random_walk.states]

    fig, ax1 = plt.subplots()
    value_func_plot = ax1.plot(random_walk.states, value_funcs, 
        label=r'Approximate MC value $\hat{v}$', color='blue')
    true_value_plot = ax1.plot(random_walk.states, true_value[1: -1], 
        label=r'True value $v_\pi$', color='red')
    ax1.set_xlabel('State')
    ax1.set_ylabel('Value scale')
    ax2 = ax1.twinx()
    state_dist_plot = ax2.plot(random_walk.states, mu[1: -1], 
        label=r'State distribution $\mu$', color='gray')
    ax2.set_ylabel('Distribution scale')
    plots = value_func_plot + true_value_plot + state_dist_plot
    labels = [l.get_label() for l in plots]
    plt.legend(plots, labels, loc=0)
    plt.savefig('./gradient_mc_state_agg.png')
    plt.close()


if __name__ == '__main__':
    n_states = 1000
    start_state = 500
    transition_radius = 100
    random_walk = RandomWalk(n_states, start_state, transition_radius)
    true_value = get_true_value(random_walk)

    gradient_mc_state_aggregation_plot(random_walk, true_value)
    









