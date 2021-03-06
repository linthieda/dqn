#!/usr/bin/env python

import tensorflow as tf
import numpy as np
import gym, sys, copy, argparse

from memory_replay import MemoryReplayer
from deep_qn import DeepQN
from tester import Tester
from plotter import Plotter

from collections import deque
import copy
from env_wrapper import EnvWrapper
import utils
import pickle
import os


def train(args=None):
    gpu_ops = tf.GPUOptions(allow_growth=True)
    config = tf.ConfigProto(gpu_options=gpu_ops, log_device_placement=False)
    sess = tf.Session(config=config)
    args_test = copy.copy(args)
    args_test.use_monitor = False
    env = EnvWrapper(args.env, mod_r=True)
    env_test = EnvWrapper(args.env, mod_r=False)


    if args.use_mr:
        print('Set experience replay ON')
    else:
        print('Set experience replay OFF')


    path = './tmp/burn_in_' + args.env + '-' + str(args.mr_capacity) + '.pickle'
    if os.path.exists(path):
        print('Found existing burn_in memory replayer, load...')
        with open(path, 'rb') as f:
            mr = pickle.load(file=f)
    else:
        mr = MemoryReplayer(env.state_shape, capacity=args.mr_capacity, enabled=args.use_mr)
        # burn_in
        mr = utils.burn_in(env, mr)


    # set type='v1' for linear model, 'v3' for three layer model (two tanh activations)

    # type='v5' use dual

    print('Set Q-network version: ', args.qn_version)
    qn = DeepQN(state_shape=env.state_shape, num_actions=env.num_actions, gamma=args.gamma, type=args.qn_version)

    qn.reset_sess(sess)

    qn.set_train(args.lr)



    if not args.reuse_model:
        print('Set reuse model      OFF')
        init = tf.global_variables_initializer()
        sess.run(init)
    else:
        print('Set reuse model      ON')
        try:
            qn.load('./tmp/qn-' + args.qn_version + '-' + args.env + '-keyinterrupt' + '.ckpt')
            optimizer_scope = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, "optimizer")
            init = tf.variables_initializer(optimizer_scope)
            sess.run(init)
            print('Found previous model')
        except tf.errors.NotFoundError:
            print('No previous model found, init new model')
            init = tf.global_variables_initializer()
            sess.run(init)

    # plotter = Plotter(save_path=args.performance_plot_path, interval=args.performance_plot_interval,
    #                   episodes=args.performance_plot_episodes)


    pretrain_test = Tester(qn, env_test, report_interval=100)
    print('Pretrain test:')
    pretrain_test.run(qn, sess)
    print('Pretrain test done.')

    tester_1 = Tester(qn, env, episodes=args.performance_plot_episodes,
                         report_interval=args.performance_plot_episodes, title='test-r-mod')
    tester_2 = Tester(qn, env_test, episodes=args.performance_plot_episodes,
                         report_interval=args.performance_plot_episodes, title='test-r-real')


    score = deque([], maxlen=args.performance_plot_episodes)
    reward_record = []

    try:
        for epi in range(args.max_episodes):
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
            score.append(rc)
            # replay
            s, s_, r, a, done = mr.replay(batch_size=args.batch_size)
            qn.train(s, s_, r, a, done)

            if (epi + 1) % args.performance_plot_interval == 0:
                print('train-r-mod reward avg: ', np.mean(score))
                tester_2.run(qn, sess)
                #r_avg, _ = tester_2.run(qn, sess)
                # reward_record.append(r_avg)
    except KeyboardInterrupt:
        qn.save('./tmp/qn-' + args.qn_version + '-' + args.env + '-keyinterrupt' + '.ckpt')
        # save mr

        with open(path, 'wb+') as f:
            pickle.dump(mr, f)
        exit(-1)


    qn.save(args.model_path)
    f = open(args.log_name, 'w')
    f.write(str(reward_record))
    f.close()
    return

def test(args):
    gpu_ops = tf.GPUOptions(allow_growth=True)
    config = tf.ConfigProto(gpu_options=gpu_ops)
    sess = tf.Session(config=config)
    env = EnvWrapper(args)
    qn = DeepQN(state_shape=env.state_shape, num_actions=env.num_actions, gamma=args.gamma, type=args.qn_version)
    qn.reset_sess(sess)
    qn.load(args.model_path)
    testor = Tester(qn, env, report_interval=args.tester_report_interval, episodes=args.tester_episodes)
    _, rs = testor.run(qn, sess, render=args.render)
    f = open(args.model_path+'_test.log', 'w')
    f.write(str(rs))
    f.close()
    return

def get_eps(t):
    return max(0.03, 0.6 - np.log10(100*t + 1) * 0.995)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Deep Q Network Argument Parser')
    parser.add_argument('--env',dest='env',type=str, default='MountainCar-v0')
    parser.add_argument('--render',dest='render',type=int,default=0)
    parser.add_argument('--train',dest='train',type=int,default=1)
    parser.add_argument('--model_path',dest='model_path',type=str, default='./tmp/blabla.ckpt')
    parser.add_argument('--use_mr', dest='use_mr', type=int, default=1)
    parser.add_argument('--mr_capacity', dest='mr_capacity', type=int, default=5000)
    parser.add_argument('--gamma', dest='gamma', type=float, default=0.99)
    parser.add_argument('--qn_version', dest='qn_version', type=str, default='v3')
    parser.add_argument('--learning_rate', dest='lr', type=float, default=0.008)
    parser.add_argument('--max_iter', dest='max_iter', type=int, default=1000000)
    parser.add_argument('--max_episodes', dest='max_episodes', type=int, default=100000)
    parser.add_argument('--batch_size', dest='batch_size', type=int, default=64)
    parser.add_argument('--performance_plot_path', dest='performance_plot_path', type=str, default='./figure/perfplot.png')
    parser.add_argument('--performance_plot_interval', dest='performance_plot_interval', type=int, default=100)
    parser.add_argument('--performance_plot_episodes', dest='performance_plot_episodes', type=int, default=100)
    parser.add_argument('--reuse_model', dest='reuse_model', type=int, default=1)
    parser.add_argument('--use_monitor', dest='use_monitor', type=int, default=0)


    return parser.parse_args()

def main(argv):
    # parse arguments
    args = parse_arguments()

    if args.use_mr == 0 and args.qn_version == 'v1':
        qnum = "q1"
    elif args.use_mr == 1 and args.qn_version == 'v1':
        qnum = "q2"
    elif args.use_mr == 1 and args.qn_version == 'v3':
        qnum = "q3"
    elif args.use_mr == 1 and args.qn_version == 'v5':
        qnum = "q4"
    elif args.use_mr == 1 and args.qn_version == 'v4' and args.env == 'SpaceInvaders-v0':
        qnum = "q5"
    else:
        print("Wrong settings!")
        return
    args.log_name = "{}_{}_data.log".format(args.env, qnum)
    args.qnum = qnum
    args.model_path = "tmp/{}_{}_model".format(args.env, qnum)
    if args.train == 1:
        train(args)
    else:
        test(args)

if __name__ == '__main__':
    main(sys.argv)