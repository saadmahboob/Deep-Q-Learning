import argparse
import datetime
import dqn
import environment
import gym
import numpy as np
import tensorflow as tf

from matplotlib import pyplot as plt

parser = argparse.ArgumentParser(description='Train an agent to play Pong.')

parser.add_argument('--load_path', help='loads a trained model from the specified path')

parser.add_argument('--save_path',
                    help='saves the model at the specified path',
                    default='checkpoints/tmp/model.ckpt')

parser.add_argument('--save_interval',
                    help='time step interval at which to save the model',
                    type=int,
                    default=30000)

parser.add_argument('--num_episodes',
                    help='number of episodes that will be played',
                    type=int,
                    default=10000)

parser.add_argument('--start_epsilon',
                    help='initial value for epsilon (exploration chance)',
                    type=float,
                    default=1)

parser.add_argument('--end_epsilon',
                    help='final value for epsilon (exploration chance)',
                    type=float,
                    default=0)

parser.add_argument('--anneal_duration',
                    help='number of episodes to decrease epsilon from start_epsilon to end_epsilon',
                    type=int,
                    default=250)

args = parser.parse_args()

load_path = args.load_path # Loads a trained model from the specified path.
save_path = args.save_path # Saves the model at the specified path.
save_interval = args.save_interval # Time step interval at which to save the model.
num_episodes = args.num_episodes # Number of episodes that will be played.
start_epsilon = args.start_epsilon # Initial value for epsilon (exploration chance).
end_epsilon = args.end_epsilon # Final value for epsilon (exploration chance).
anneal_duration = args.anneal_duration # Number of episodes needed to decrease epsilon from
                                       # start_epsilon to end_epsilon.

batch_size = 1024 # Number of experiences sampled and trained on at once.
wait_before_training = 5000 # Number of experiences to accumulate before training starts.
train_interval = 100 # Number of experiences to accumulate before another round of training starts.
discount = 0.99 # Discount factor for future rewards.

env = environment.AtariWrapper(gym.make('Pong-v0'),
                               action_space=[0, 2, 3], # 'NONE', 'UP' and 'DOWN'.
                               observations_per_state=4,
                               replay_memory_capacity=24000)

epsilon_history = []
reward_history = []

with tf.Session() as sess:
    network = dqn.DeepQNetwork(sess, len(env.action_space), env.state_space)
    sess.run(tf.initialize_all_variables())
    saver = tf.train.Saver()

    if load_path:
        saver.restore(sess, load_path)
        print('Model restored.')

    epsilon = start_epsilon
    t = 0

    for i in range(num_episodes):
        # Epsilon anneals from start_epsilon to end_epsilon.
        epsilon = max(end_epsilon,
                      (start_epsilon * (anneal_duration - i) + end_epsilon * i) / anneal_duration)
        episode_reward = 0
        episode_loss = []

        while not env.done:
            t += 1
            env.render()

            # Occasionally train.
            if t > wait_before_training and t % train_interval == 0:
                # These operations might be confusing if you forget that they're vectorized.
                experiences = env.sample_experiences(batch_size)
                states = np.stack(experiences[:, 0], axis=0)
                actions_i = np.stack([env.action_space.index(a) for a in experiences[:, 1]], axis=0)
                rewards = np.stack(experiences[:, 2], axis=0)
                next_states = np.stack(experiences[:, 3], axis=0)
                done = np.stack(experiences[:, 4], axis=0)

                # Determine the true action values.
                #
                #                    { r, if next state is terminal
                # Q(state, action) = {
                #                    { r + discount * max(Q(next state, <any action>)), otherwise
                Q_ = rewards + ~done * discount * network.eval_optimal_action_value(next_states)
                
                # Estimate action values, measure errors and update weights.
                network.train(states, actions_i, Q_, learning_rate=1e-6)

            # Occasionally try a random action (explore).
            if np.random.rand() < epsilon:
                action = env.sample_action()
            else:
                state = np.expand_dims(env.get_state(), axis=0)
                action = env.action_space[network.eval_optimal_action(state)[0]]

            episode_reward += env.step(action)

            if save_path and t % save_interval == 0:
                saver.save(sess, save_path)
                print('[{}] Saved model at "{}".'.format(datetime.datetime.now(), save_path))

        epsilon_history.append(epsilon)
        reward_history.append(episode_reward)
        print('Episode: {}  Reward: {}  Epsilon: {}'.format(i + 1, episode_reward, epsilon))
        env.restart()

if save_path:
    saver.save(sess, save_path)
    print('[{}] Saved model at "{}".'.format(datetime.datetime.now(), save_path))

print('Total timesteps:', t)

plt.subplot(211)
plt.ylabel('Reward')
plt.xlabel('Episode')
plt.plot(reward_history)

plt.subplot(212)
plt.ylabel('Explore / Exploit')
plt.xlabel('Episode')
plt.plot(epsilon_history)

plt.tight_layout()
plt.show()
