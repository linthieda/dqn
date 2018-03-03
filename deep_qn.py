#!/usr/bin/env python

import tensorflow as tf
import numpy as np
import gym, sys, copy, argparse


class DeepQN(object):
    def __init__(self, state_dim, num_actions, gamma=1.0):
        self.sess = None
        self.num_actions = num_actions
        self.s = tf.placeholder(dtype=tf.float32,
                                 shape=[None, state_dim],
                                 name='s')

        self.a = tf.placeholder(dtype=tf.int32,
                                shape=None,
                                name='a')

        self.r = tf.placeholder(dtype=tf.float32,
                                shape=[None],
                                name='r')

        self.h1 = tf.layers.dense(inputs=self.s,
                                 units=24,
                                 activation=tf.nn.tanh,
                                 use_bias=True,
                                 kernel_initializer=tf.random_normal_initializer(),
                                 bias_initializer=tf.zeros_initializer(),
                                 name='h1',
                                 trainable=True,
                                 reuse=None)

        self.h2 = tf.layers.dense(inputs=self.h1,
                                 units=48,
                                 activation=tf.nn.tanh,
                                 use_bias=True,
                                 kernel_initializer=tf.random_normal_initializer(),
                                 bias_initializer=tf.zeros_initializer(),
                                 name='h2',
                                 trainable=True,
                                 reuse=None)

        self.q = tf.layers.dense(inputs=self.h2,
                                 units=num_actions,
                                 activation=None,
                                 use_bias=True,
                                 kernel_initializer=tf.random_normal_initializer(),
                                 bias_initializer=tf.zeros_initializer(),
                                 name='q',
                                 trainable=True,
                                 reuse=None)



        self.q_ = tf.placeholder(dtype=tf.float32,
                                shape=[None],
                                name='q_')


        a_indices = tf.stack([tf.range(tf.shape(self.a)[0], dtype=tf.int32), self.a], axis=1)

        self.estimate = tf.gather_nd(params=self.q, indices=a_indices)  # shape=(None, )

        target = gamma * self.q_ + self.r

        self.target = tf.stop_gradient(target)

        self.loss = tf.reduce_mean(tf.squared_difference(self.target, self.estimate))

        return

    def reset_sess(self, sess):
        self.sess = sess

    def set_train(self, lr):
        self.train_op = tf.train.AdamOptimizer().minimize(self.loss)

    def predict(self, state):
        if state.ndim == 1:
            state = state.reshape([1, -1])
        return self.sess.run(self.q, {self.s: state})

    def select_action_greedy(self, state):
        q = self.predict(state)
        return np.argmax(q, axis=1)

    def select_action_eps_greedy(self, eps, state):
        if np.random.uniform(low=0.0, high=1.0) < eps:
            return [np.random.randint(0, self.num_actions)]
        else:
            return self.select_action_greedy(state)

    def train(self, s, s_, r, a, done):
        q_ = self.predict(s_)
        qa_ = np.max(q_, axis=1)
        qa_ = np.where(done, 0, qa_)
        self.sess.run(self.train_op, {self.s: s,
                                      self.q_: qa_,
                                      self.r: r,
                                      self.a: a})
        return



