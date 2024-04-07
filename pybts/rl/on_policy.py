import numpy as np
from gymnasium import spaces
from stable_baselines3.common.on_policy_algorithm import OnPolicyAlgorithm
from stable_baselines3.common.utils import explained_variance, get_schedule_fn, safe_mean, obs_as_tensor
import typing
import torch as th


def bt_on_policy_collect_rollouts(model: OnPolicyAlgorithm, last_obs) -> typing.Iterator:
    assert last_obs is not None, "No previous observation was provided"
    model._last_obs = last_obs
    # Switch to eval mode (this affects batch norm / dropout)
    model.policy.set_training_mode(False)
    n_steps = 0
    model.rollout_buffer.reset()
    # Sample new weights for the state dependent exploration
    if model.use_sde:
        model.policy.reset_noise(1)

    # callback.on_rollout_start()
    while n_steps < model.n_steps:
        if model.use_sde and model.sde_sample_freq > 0 and n_steps % model.sde_sample_freq == 0:
            # Sample a new noise matrix
            model.policy.reset_noise(1)

        with th.no_grad():
            # Convert to pytorch tensor or to TensorDict
            obs_tensor = obs_as_tensor(model._last_obs, model.device)
            actions, values, log_probs = model.policy(obs_tensor)
        actions = actions.cpu().numpy()

        # Rescale and perform action
        clipped_actions = actions

        if isinstance(model.action_space, spaces.Box):
            if model.policy.squash_output:
                # Unscale the actions to match env bounds
                # if they were previously squashed (scaled in [-1, 1])
                clipped_actions = model.policy.unscale_action(clipped_actions)
            else:
                # Otherwise, clip the actions to avoid out of bound error
                # as we are sampling from an unbounded Gaussian distribution
                clipped_actions = np.clip(actions, model.action_space.low, model.action_space.high)

        new_obs, reward, done, info = yield clipped_actions

        rewards = np.array([reward])
        dones = np.array([done])
        infos = [info]

        model.num_timesteps += 1

        # Give access to local variables
        # callback.update_locals(locals())
        # if not callback.on_step():
        #     return False

        model._update_info_buffer(infos, dones)
        n_steps += 1

        if isinstance(model.action_space, spaces.Discrete):
            # Reshape in case of discrete action
            actions = actions.reshape(-1, 1)

        # Handle timeout by bootstraping with value function
        # see GitHub issue #633
        for idx, done in enumerate(dones):
            if (
                    done
                    and infos[idx].get("terminal_observation") is not None
                    and infos[idx].get("TimeLimit.truncated", False)
            ):
                terminal_obs = model.policy.obs_to_tensor(infos[idx]["terminal_observation"])[0]
                with th.no_grad():
                    terminal_value = model.policy.predict_values(terminal_obs)[0]  # type: ignore[arg-type]
                rewards[idx] += model.gamma * terminal_value

        model.rollout_buffer.add(
                model._last_obs,  # type: ignore[arg-type]
                actions,
                rewards,
                model._last_episode_starts,  # type: ignore[arg-type]
                values,
                log_probs,
        )
        model._last_obs = new_obs  # type: ignore[assignment]
        model._last_episode_starts = dones

    with th.no_grad():
        # Compute value for the last timestep
        values = model.policy.predict_values(obs_as_tensor(new_obs, model.device))  # type: ignore[arg-type]

    model.rollout_buffer.compute_returns_and_advantage(last_values=values, dones=dones)


def bt_on_policy_predict(model: OnPolicyAlgorithm, last_obs):
    # Switch to eval mode (this affects batch norm / dropout)
    model._last_obs = last_obs
    model.policy.set_training_mode(False)
    with th.no_grad():
        # Convert to pytorch tensor or to TensorDict
        obs_tensor = obs_as_tensor(model._last_obs, model.device)
        actions, values, log_probs = model.policy(obs_tensor)
    actions = actions.cpu().numpy()
    # Rescale and perform action
    clipped_actions = actions

    if isinstance(model.action_space, spaces.Box):
        if model.policy.squash_output:
            # Unscale the actions to match env bounds
            # if they were previously squashed (scaled in [-1, 1])
            clipped_actions = model.policy.unscale_action(clipped_actions)
        else:
            # Otherwise, clip the actions to avoid out of bound error
            # as we are sampling from an unbounded Gaussian distribution
            clipped_actions = np.clip(actions, model.action_space.low, model.action_space.high)

    # self.actions.put_nowait(clipped_actions)
    return clipped_actions
