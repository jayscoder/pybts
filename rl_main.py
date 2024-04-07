import gymnasium as gym

from stable_baselines3 import SAC, PPO
from stable_baselines3.common.env_util import make_vec_env
import time

vec_env = make_vec_env("Pendulum-v1", n_envs=4, seed=0)

# We collect 4 transitions per call to `ènv.step()`
# and performs 2 gradient steps per call to `ènv.step()`
# if gradient_steps=-1, then we would do 4 gradients steps per call to `ènv.step()`
model = PPO("MlpPolicy", vec_env, verbose=1, device='cpu', n_steps=1, batch_size=2)
start_time = time.time()
model.learn(total_timesteps=10000, progress_bar=True)  # cpu: 28s mps:71s
print('Cost time: ', time.time() - start_time)

if __name__ == '__main__':
    pass
