import tensorflow as tf

# import rltf.models as models
from rltf               import agents
from rltf               import models
from rltf.cmdutils      import ArgSpec
from rltf.exploration   import DecayedExplorationNoise
from rltf.exploration   import GaussianNoise #pylint: disable=unused-import
from rltf.exploration   import OrnsteinUhlenbeckNoise
from rltf.optimizers    import OptimizerConf
from rltf.schedules     import ConstSchedule #pylint: disable=unused-import
from rltf.schedules     import PiecewiseSchedule


RMSPropOptimizer  = RMSProp = tf.train.RMSPropOptimizer
AdamOptimizer     = Adam    = tf.train.AdamOptimizer


dqn_spec = dict(
  warm_up=50000,                # Number of *agent* steps before training starts
  train_period=4,               # Period for taking a training step (in number of *agent* steps)
  target_update_period=10000,   # Period for updating the target network (in number of *agent* steps)
  stop_step=50*10**6,           # Total number of *agent* steps
  eval_period=250000,           # Period of running evaluation (in number of *agent* steps)
  eval_len=125000,              # Lenght of each evaluation run (in number of *agent* steps)
  batch_size=32,                # Mini-batch size
  gamma=0.99,                   # Discount factor
  memory_size=10**6,            # Size of the replay buffer
  stack_frames=4,               # Number of stacked frames that make an observation
  log_period=50000,             # Period for logging progress (in number of *agent* steps)
  save_period=10**6,            # Period for saving progress (in number of *agent* steps)
  video_period=1000,            # Period for recording episode videos (in number of episodes)
  save_buf=True,                # Save the replay buffer
  # environment arguments
  env_kwargs=ArgSpec(dict, max_ep_steps_train=108000, max_ep_steps_eval=108000)
)



DQN = {**dqn_spec, **dict(
  agent=agents.AgentDQN,
  model=models.DQN,
  huber_loss=True,
  opt_conf=ArgSpec(OptimizerConf, opt_type=RMSPropOptimizer, learn_rate=25e-5, epsilon=1e-5, decay=0.95),
  # Original DQN has slightly different epsilon_train schedule
  epsilon_train=ArgSpec(PiecewiseSchedule, endpoints=[(0, 1.0), (10**6, 0.01)], outside_value=0.01),
  epsilon_eval=0.001,
)}

DDQN = {**dqn_spec, **dict(
  agent=agents.AgentDQN,
  model=models.DDQN,
  huber_loss=True,
  opt_conf=ArgSpec(OptimizerConf, opt_type=RMSPropOptimizer, learn_rate=25e-5, epsilon=1e-5, decay=0.95),
  epsilon_train=ArgSpec(PiecewiseSchedule, endpoints=[(0, 1.0), (10**6, 0.01)], outside_value=0.01),
  epsilon_eval=0.001,
)}

BstrapDQN = {**dqn_spec, **dict(
  agent=agents.AgentDQN,
  model=models.BstrapDQN,
  n_heads=10,                   # Number of bootstrap heads
  huber_loss=True,
  opt_conf=ArgSpec(OptimizerConf, opt_type=RMSPropOptimizer, learn_rate=25e-5, epsilon=1e-5, decay=0.95),
  epsilon_train=ArgSpec(PiecewiseSchedule, endpoints=[(0, 1.0), (10**6, 0.01)], outside_value=0.01),
  epsilon_eval=0.001,
)}

C51 = {**dqn_spec, **dict(
  agent=agents.AgentDQN,
  model=models.C51,
  V_min=-10,                    # Lower bound for distribution support
  V_max=10,                     # Upper bound for distribution support
  N=51,                         # Number of distribution atoms
  opt_conf=ArgSpec(OptimizerConf, opt_type=tf.train.AdamOptimizer, learn_rate=25e-5, epsilon=.01/32),
  epsilon_train=ArgSpec(PiecewiseSchedule, endpoints=[(0, 1.0), (10**6, 0.01)], outside_value=0.01),
  epsilon_eval=0.001,
)}

QRDQN = {**dqn_spec, **dict(
  agent=agents.AgentDQN,
  model=models.QRDQN,
  N=200,                        # Number of quantiles
  k=1,                          # Quantile Huber loss order
  opt_conf=ArgSpec(OptimizerConf, opt_type=tf.train.AdamOptimizer, learn_rate=5e-5, epsilon=.01/32),
  epsilon_train=ArgSpec(PiecewiseSchedule, endpoints=[(0, 1.0), (10**6, 0.01)], outside_value=0.01),
  epsilon_eval=0.001,
)}

BstrapDQN_UCB = {**BstrapDQN, **dict(
  n_stds=0.1,
  target_update_period=40000,
)}

BstrapDQN_Ensemble = {**BstrapDQN}


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


DDPG = dict(
  agent=agents.AgentDDPG,
  model=models.DDPG,
  obs_norm=False,               # Normalize observations
  batch_norm=False,             # Apply batch normalization in the critic
  critic_reg=0.0,               # Critic weight regularization hyperparameter
  critic_huber_loss=False,      # Use huber loss for the critic
  tau=0.001,                    # Weight for soft target update
  batch_size=64,                # Mini-batch size. Set to 16 for image observations
  gamma=0.99,                   # Discount factor
  memory_size=10**6,            # Size of the replay buffer
  stack_frames=3,               # Number of stacked frames that make an observation
  actor_opt_conf=ArgSpec(OptimizerConf,  opt_type=tf.train.AdamOptimizer, learn_rate=1e-4),
  critic_opt_conf=ArgSpec(OptimizerConf, opt_type=tf.train.AdamOptimizer, learn_rate=1e-3),
  action_noise=lambda shape=(1,): ArgSpec(DecayedExplorationNoise,
      # Additive action space noise
      noise=ArgSpec(OrnsteinUhlenbeckNoise, shape=shape, mu=0.0, sigma=0.5, theta=0.15, dt=1e-2),
      # Rate for which to decay the weight of the action noise from 1 to 0; not in original DDPG
      decay=ArgSpec(PiecewiseSchedule, endpoints=[(0, 1.0), (500000, 0.0)], outside_value=0.0)
    ),
  warm_up=10000,                # Number of *agent* steps before training starts
  train_period=1,               # Period for taking a training step (in number of *agent* steps)
  target_update_period=1,       # Period for updating the target network (in number of *agent* steps)
  stop_step=2500000,            # Total number of *agent* steps
  eval_period=500000,           # Period of running evaluation (in number of *agent* steps)
  eval_len=50000,               # Lenght of each evaluation run (in number of *agent* steps)
  log_period=50000,             # Period for logging progress (in number of *agent* steps)
  video_period=500,             # Period for recording episode videos (in number of episodes)
  save_period=500000,           # Period for saving progress (in number of *agent* steps)
  save_buf=True,                # Save the replay buffer
  # environment arguments
  env_kwargs=ArgSpec(dict, max_ep_steps_train=None, max_ep_steps_eval=None, rew_scale=1.0)
)


REINFORCE = dict(
  agent=agents.AgentPG,
  model=models.REINFORCE,
  pi_opt_conf=ArgSpec(OptimizerConf, opt_type=tf.train.AdamOptimizer, learn_rate=5e-3),
  vf_opt_conf=ArgSpec(OptimizerConf, opt_type=tf.train.AdamOptimizer, learn_rate=5e-3),
  layers=[64, 64],              # Network layer sizes
  activation=tf.tanh,           # Network activation function
  obs_norm=False,               # Normalize observations
  nn_std=False,                 # If True, stddev of a Gaussian policy is a function of the state
  gamma=0.99,                   # Discount factor
  lam=0.97,                     # Lambda value for GAE(gamma, lambda)
  path_len=1000,                # Number of agent steps before taking a policy gradient step
  stop_step=1000000,            # Total environment interaction steps
  vf_iters=1,                   # Number of value function training iterations per epochs
  stack_frames=3,               # Number of stacked frames that make an observation
  eval_period=10,               # Period of running evaluation (in number of epochs)
  eval_len=1000,                # Lenght of each evaluation run (in number of *agent* steps)
  log_period=1,                 # Period for logging progress (in number of *agent* steps)
  video_period=500,             # Period for recording episode videos (in number of episodes)
  save_period=10,               # Period for saving progress (in number of *agent* steps)
  # environment arguments
  env_kwargs=ArgSpec(dict, max_ep_steps_train=None, max_ep_steps_eval=None, rew_scale=1.0),
)


PPO = dict(
  agent=agents.AgentPPO,
  model=models.PPO,
  pi_opt_conf=ArgSpec(OptimizerConf, opt_type=tf.train.AdamOptimizer, learn_rate=5e-3),
  vf_opt_conf=ArgSpec(OptimizerConf, opt_type=tf.train.AdamOptimizer, learn_rate=5e-3),
  layers=[64, 64],              # Network layer sizes
  activation=tf.tanh,           # Network activation function
  obs_norm=False,               # Normalize observations
  nn_std=False,                 # If True, stddev of a Gaussian policy is a function of the state
  ent_weight=0.1,               # Weight coefficient for entropy in the total loss
  vf_weight=0.5,                # Weight coefficient for value function loss in the total loss
  gamma=0.99,                   # Discount factor
  lam=0.95,                     # Lambda value for GAE(gamma, lambda)
  path_len=1000,                # Number of agent steps before taking a policy gradient step
  train_steps=4,                # Number of training epochs per single data collection session
  batch_size=512,               # Batch size for training the model
  clip_range=ArgSpec(ConstSchedule, value=0.2),   # Clipping value for PPO objective
  stop_step=1000000,            # Total environment interaction steps
  stack_frames=3,               # Number of stacked frames that make an observation
  eval_period=10,               # Period of running evaluation (in number of epochs)
  eval_len=1000,                # Lenght of each evaluation run (in number of *agent* steps)
  log_period=1,                 # Period for logging progress (in number of *agent* steps)
  video_period=500,             # Period for recording episode videos (in number of episodes)
  save_period=10,               # Period for saving progress (in number of *agent* steps)
  # environment arguments
  env_kwargs=ArgSpec(dict, max_ep_steps_train=None, max_ep_steps_eval=None, rew_scale=1.0),
)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


MODELS = dict(
  DQN=DQN,
  DDQN=DDQN,
  C51=C51,
  QRDQN=QRDQN,
  BstrapDQN=BstrapDQN,
  BstrapDQN_UCB=BstrapDQN_UCB,
  BstrapDQN_Ensemble=BstrapDQN_Ensemble,
  DDPG=DDPG,
  REINFORCE=REINFORCE,
  PPO=PPO,
)


def get_args(model):
  return MODELS[model]