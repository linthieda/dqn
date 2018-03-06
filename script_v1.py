#!/usr/bin/env python

import tensorflow as tf
import numpy as np
import gym, sys, copy, argparse

from memory_replay import MemoryReplayer
from deep_qn import DeepQN
from tester import Tester
from plotter import Plotter

from env_wrapper import EnvWrapper


def train():
    print(tf.__version__)
    gpu_ops = tf.GPUOptions(allow_growth=True)
    config = tf.ConfigProto(gpu_options=gpu_ops, log_device_placement=False)
    sess = tf.Session(config=config)

    env_name = 'CartPole-v0'
    has_memrory = False
    qn_ver = 'v1'

    if not has_memrory and qn_ver == 'v1':
        log_name = "{}-v0_q1_data.log".format(env_name)
    elif has_memrory and qn_ver == 'v1':
        log_name = "{}-v0_q2_data.log".format(env_name)
    elif has_memrory and qn_ver == 'v3':
        log_name = "{}-v0_q3_data.log".format(env_name)
    elif has_memrory and qn_ver == 'v5':
        log_name = "{}-v0_q4_data.log".format(env_name)
    elif has_memrory and qn_ver == 'v4' and env_name == 'SpaceInvaders-v0':
        log_name = "{}-v0_q5_data.log".format(env_name)
    else:
        print("Wrong settings!")

    env = EnvWrapper(env_name)
    env_test = EnvWrapper(env_name)

    mr = MemoryReplayer(env.state_shape, capacity=100000, enabled=has_memrory)

    # set type='v1' for linear model, 'v3' for three layer model (two tanh activations)

    # type='v5' use dual

    qn = DeepQN(state_shape=env.state_shape, num_actions=env.num_actions, gamma=0.99, type=qn_ver)


    qn.reset_sess(sess)

    qn.set_train(0.001)

    init = tf.global_variables_initializer()
    sess.run(init)

    plotter = Plotter()

    pretrain_test = Tester(qn, env, report_interval=100)
    print('Pretrain test:')
    pretrain_test.run(qn, sess)
    print('Pretrain test done.')

    test = Tester(qn, env_test, 20, 20)

    score = []
    reward_record = []
    cnt_iter = 0

    for epi in range(1000000):
        s = env.reset()

        done = False

        rc = 0

        while not done:
            a = qn.select_action_eps_greedy(get_eps(epi), s)
            a_ = a[0]
            s_, r, done, _ = env.step(a_)
            mr.remember(s, s_, r, a_, done)
            s = s_
            rc += r
            cnt_iter += 1
            if (cnt_iter + 1) % 10000 == 0:
                reward_record.append(test.run(qn, sess))

        score.append(rc)

        # replay

        s, s_, r, a, done = mr.replay(batch_size=64)

        qn.train(s, s_, r, a, done)

        if cnt_iter > 1000000:
            break

        # if (epi + 1) % 200 == 0:
        #     avg_score = np.mean(score)
        #     plotter.plot(avg_score)
        #     print('avg score last 200 episodes ', avg_score)
        #     score = []
        #     if avg_score > 195:
        #         break

    f = open(log_name, 'w')
    f.write(str(reward_record))
    f.close()
    return

def test(render=False, path='./tmp/dqn_v3.ckpt', episodes=100):
    gpu_ops = tf.GPUOptions(allow_growth=True)
    config = tf.ConfigProto(gpu_options=gpu_ops)
    sess = tf.Session(config=config)

    qn = DeepQN(state_shape=(2,), num_actions=3, gamma=0.99)

    qn.reset_sess(sess)

    qn.load(path)

    env = gym.make('MountainCar-v0')

    testor = Tester(qn, env, report_interval=100, episodes=episodes)

    testor.run(qn, sess, render=render)

    return

def get_eps(t):
    return max(0.01, 1.0 - np.log10(t + 1) * 0.995)

def main():
    train()

if __name__ == '__main__':
    main()