from sandbox.rocky.tf.q_functions.base import QFunction
import sandbox.rocky.tf.core.layers as L
import tensorflow as tf
from rllab.core.serializable import Serializable
from sandbox.rocky.tf.core.layers_powered import LayersPowered
from sandbox.rocky.tf.misc import tensor_utils


class ContinuousMLPQFunction(QFunction, LayersPowered, Serializable):
    def __init__(
            self,
            env_spec,
            name='qnet',
            hidden_sizes=(32, 32),
            hidden_nonlinearity=tf.nn.relu,
            action_merge_layer=-2,
            output_nonlinearity=None,
            hidden_W_init=L.XavierUniformInitializer(),
            hidden_b_init=tf.zeros_initializer(),
            output_W_init=L.XavierUniformInitializer(),
            output_b_init=tf.zeros_initializer(),
            bn=False):
        Serializable.quick_init(self, locals())

        with tf.variable_scope(name):
            l_obs = L.InputLayer(shape=(None, env_spec.observation_space.flat_dim), name="obs")
            l_action = L.InputLayer(shape=(None, env_spec.action_space.flat_dim), name="actions")

            n_layers = len(hidden_sizes) + 1

            if n_layers > 1:
                action_merge_layer = \
                    (action_merge_layer % n_layers + n_layers) % n_layers
            else:
                action_merge_layer = 1

            l_hidden = l_obs

            for idx, size in enumerate(hidden_sizes):
                if bn:
                    l_hidden = L.batch_norm(l_hidden)

                if idx == action_merge_layer:
                    l_hidden = L.ConcatLayer([l_hidden, l_action])

                l_hidden = L.DenseLayer(
                    l_hidden,
                    num_units=size,
                    W=hidden_W_init,
                    b=hidden_b_init,
                    nonlinearity=hidden_nonlinearity,
                    name="h%d" % (idx + 1)
                )

            if action_merge_layer == n_layers:
                l_hidden = L.ConcatLayer([l_hidden, l_action])

            l_output = L.DenseLayer(
                l_hidden,
                num_units=1,
                W=output_W_init,
                b=output_b_init,
                nonlinearity=output_nonlinearity,
                name="output"
            )

            #output_var = L.get_output(l_output, deterministic=True).flatten()
            output_var = tf.reshape(L.get_output(l_output, deterministic=True),(-1,))

            self._f_qval = tensor_utils.compile_function([l_obs.input_var, l_action.input_var], output_var)
            self._output_layer = l_output
            self._obs_layer = l_obs
            self._action_layer = l_action
            self._output_nonlinearity = output_nonlinearity

            LayersPowered.__init__(self, [l_output])

    def get_qval(self, observations, actions):
        return self._f_qval(observations, actions)

    def get_qval_sym(self, obs_var, action_var, **kwargs):
        qvals = L.get_output(
            self._output_layer,
            {self._obs_layer: obs_var, self._action_layer: action_var},
            **kwargs
        )
        return tf.reshape(qvals, (-1,))
