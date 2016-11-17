"""Defines an agent that learns to play Atari games using deep Q-learning.

Heavily influenced by DeepMind's seminal paper 'Playing Atari with Deep Reinforcement Learning'
(Mnih et al., 2013).
"""

import dqn
import numpy as np
import tensorflow as tf


class Agent():
    def __init__(self,
                 sess,
                 env,
                 start_epsilon=1,
                 end_epsilon=0,
                 anneal_duration=500,
                 wait_before_training=5000,
                 train_interval=100,
                 batch_size=1024,
                 discount=0.99):
        """An agent that learns to play Atari games using deep Q-learning.

        Args:
            sess: The associated TensorFlow session.
            env: An AtariWrapper object (see 'environment.py') that wraps over an OpenAI Gym Atari
                environment.
            start_epsilon: Initial value for epsilon (exploration chance).
            end_epsilon: Final value for epsilon (exploration chance).
            anneal_duration: Number of episodes needed to decrease epsilon from start_epsilon to
                end_epsilon.
            wait_before_training: Number of experiences to accumulate before training starts.
            train_interval: Number of experiences to accumulate before another round of training
                starts.
            batch_size: Number of experiences sampled and trained on at once.
            discount: Discount factor for future rewards.
        """
        
        self.sess = sess
        self.env = env
        self.dqn = dqn.DeepQNetwork(sess, len(env.action_space), env.state_space)
        self.start_epsilon = start_epsilon
        self.end_epsilon = end_epsilon
        self.anneal_duration = anneal_duration
        self.wait_before_training = wait_before_training
        self.train_interval = train_interval
        self.batch_size = batch_size
        self.discount = discount
        self.t = 0
        self.episodes_played = 0

    def train(self, render=True, learning_rate=1e-6):
        if self.env.done:
            self.env.restart()

        self.episodes_played += 1
        episode_reward = 0
        epsilon = self._get_epsilon()

        while not self.env.done:
            self.t += 1
            
            if render:
                self.env.render()

            # Occasionally train.
            if self.t > self.wait_before_training and self.t % self.train_interval == 0:
                states, actions, rewards, next_states, done = self.env.sample_experiences(self.batch_size)
                actions_i = np.stack([self.env.action_space.index(a) for a in actions], axis=0)

                # Determine the true action values.
                #
                #                    { r, if next state is terminal
                # Q(state, action) = {
                #                    { r + discount * max(Q(next state, <any action>)), otherwise
                Q_ = rewards + ~done * self.discount * self.dqn.eval_optimal_action_value(next_states)
                
                # Estimate action values, measure errors and update weights.
                self.dqn.train(states, actions_i, Q_, learning_rate=learning_rate)

            # Occasionally try a random action (explore).
            if np.random.rand() < epsilon:
                action = self.env.sample_action()
            else:
                state = np.expand_dims(self.env.get_state(), axis=0)
                action = self.env.action_space[self.dqn.eval_optimal_action(state)[0]]

            episode_reward += self.env.step(action)

        return episode_reward

    def play(self, render=True):
        if self.env.done:
            self.env.restart()

        episode_reward = 0

        while not self.env.done:
            if render:
                self.env.render()

            state = np.expand_dims(self.env.get_state(), axis=0)
            action = self.env.action_space[self.dqn.eval_optimal_action(state)[0]]
            episode_reward += self.env.step(action)

        return episode_reward

    def _get_epsilon(self):
        """Gets the epsilon value (exploration chance) for the current episode."""

        # Epsilon anneals from start_epsilon to end_epsilon.
        if self.anneal_duration == 0:
            return self.end_epsilon

        start_weight = (self.anneal_duration - self.episodes_played) / self.anneal_duration
        end_weight = self.episodes_played / self.anneal_duration

        return max(self.end_epsilon,
                   self.start_epsilon * start_weight + self.end_epsilon * end_weight)