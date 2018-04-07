import numpy      as np
import tensorflow as tf

from rltf.models  import BaseDQN


class C51(BaseDQN):

  def __init__(self, obs_shape, n_actions, opt_conf, gamma, V_min, V_max, N):
    """
    Args:
      obs_shape: list. Shape of the observation tensor
      n_actions: int. Number of possible actions
      opt_conf: rltf.optimizers.OptimizerConf. Configuration for the optimizer
      gamma: float. Discount factor
      V_min: float. lower bound for histrogram range
      V_max: float. upper bound for histrogram range
      N: int. number of histogram bins
    """

    super().__init__(obs_shape, n_actions, opt_conf, gamma)

    self.N      = N
    self.V_min  = V_min
    self.V_max  = V_max
    self.dz     = (self.V_max - self.V_min) / float(self.N - 1)

    # Custom TF Tensors and Ops
    self.bins   = None


  def build(self):

    # Costruct the tensor of the bins for the probability distribution
    bins          = np.arange(self.V_min, self.V_max + self.dz, self.dz)
    self.bins     = tf.constant(bins, dtype=tf.float32)

    super().build()


  def _nn_model(self, x, scope):
    """ Build the C51 architecture - as desribed in the original paper

    Args:
      x: tf.Tensor. Tensor for the input
      scope: str. Scope in which all the model related variables should be created

    Returns:
      `tf.Tensor` of shape `[batch_size, n_actions, N]`. Contains the distribution of Q for each action
    """
    n_actions = self.n_actions
    N         = self.N

    with tf.variable_scope(scope, reuse=False):
      with tf.variable_scope("convnet"):
        # original architecture
        x = tf.layers.conv2d(x, filters=32, kernel_size=8, strides=4, padding="SAME", activation=tf.nn.relu)
        x = tf.layers.conv2d(x, filters=64, kernel_size=4, strides=2, padding="SAME", activation=tf.nn.relu)
        x = tf.layers.conv2d(x, filters=64, kernel_size=3, strides=1, padding="SAME", activation=tf.nn.relu)
      x = tf.layers.flatten(x)
      with tf.variable_scope("action_value"):
        x = tf.layers.dense(x, units=512,            activation=tf.nn.relu)
        x = tf.layers.dense(x, units=N*n_actions,  activation=None)

      # Compute Softmax probabilities in numerically stable way
      x = tf.reshape(x, [-1, n_actions, N])
      x = x - tf.expand_dims(tf.reduce_max(x, axis=-1), axis=-1)
      x = tf.nn.softmax(x, dim=-1)
      return x


  def _compute_estimate(self, agent_net):
    # Get the Z-distribution for the selected action; output shape [None, N]
    act_t     = tf.cast(self._act_t_ph, tf.int32)
    act_mask  = tf.one_hot(act_t, self.n_actions, on_value=True, off_value=False, dtype=tf.bool)
    z         = tf.boolean_mask(agent_net, act_mask)
    return z


  def _compute_target(self, agent_net, target_net):
    target_z      = target_net

    # Get the target Q probabilities for the greedy action; output shape [None, N]
    target_q      = tf.reduce_sum(target_z * self.bins, axis=-1)
    target_act    = tf.argmax(target_q, axis=-1)
    act_mask      = tf.one_hot(target_act, self.n_actions, on_value=True, off_value=False, dtype=tf.bool)
    target_z      = tf.boolean_mask(target_z, act_mask)

    # Compute projected bin support; output shape [None, N]
    done_mask     = tf.cast(tf.logical_not(self.done_ph), tf.float32)
    done_mask     = tf.expand_dims(done_mask, axis=-1)
    rew_t         = tf.expand_dims(self.rew_t_ph, axis=-1)
    bins          = tf.expand_dims(self.bins, axis=0)
    target_bins   = rew_t + self.gamma * done_mask * bins
    target_bins   = tf.clip_by_value(target_bins, self.V_min, self.V_max)

    # Projected bin indices; output shape [None, N], dtype=float
    bin_inds      = (target_bins - self.V_min) / self.dz
    bin_inds_lo   = tf.floor(bin_inds)
    bin_inds_hi   = tf.ceil(bin_inds)

    lo_add        = target_z * (bin_inds_hi - bin_inds)
    hi_add        = target_z * (bin_inds - bin_inds_lo)

    # Initialize the Variable holding the target distribution - gets reset to 0 every time
    # zeros         = tf.zeros_like(self.done_ph, dtype=tf.float32)
    zeros         = tf.zeros_like(target_bins, dtype=tf.float32)
    target_z      = tf.Variable(0, trainable=False, dtype=tf.float32, validate_shape=False)
    target_z      = tf.assign(target_z, zeros, validate_shape=False)
    # tz      = tf.Variable(0, trainable=False, dtype=tf.float32, validate_shape=False)
    # target_z      = tf.assign(tz, zeros, validate_shape=False)

    # Compute indices for scatter_nd_add
    batch         = tf.shape(self.done_ph)[0]
    row_inds      = tf.range(0, limit=batch, delta=1, dtype=tf.int32)
    row_inds      = tf.tile(tf.expand_dims(row_inds, axis=-1), [1, self.N])
    row_inds      = tf.expand_dims(row_inds, axis=-1)
    bin_inds_lo   = tf.concat([row_inds, tf.expand_dims(tf.to_int32(bin_inds_lo), axis=-1)], axis=-1)
    bin_inds_hi   = tf.concat([row_inds, tf.expand_dims(tf.to_int32(bin_inds_hi), axis=-1)], axis=-1)

    with tf.control_dependencies([target_z]):
      target_z    = tf.scatter_nd_add(target_z, bin_inds_lo, lo_add, use_locking=True)
      target_z    = tf.scatter_nd_add(target_z, bin_inds_hi, hi_add, use_locking=True)

    return target_z


  def _compute_loss(self, estimate, target):
    z         = estimate
    target_z  = target
    entropy   = -tf.reduce_sum(target_z * tf.log(z), axis=-1)
    loss      = tf.reduce_mean(entropy)

    return loss

  def _act_train(self, agent_net, name):
    # Compute the Q-function as expectation of Z; output shape [None, n_actions]
    q       = tf.reduce_sum(agent_net * self.bins, axis=-1)
    action  = tf.argmax(q, axis=-1, output_type=tf.int32, name=name)
    return action


  def _act_eval(self, agent_net, name):
    return None