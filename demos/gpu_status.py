import pybts
import GPUtil
import time


class GPUNode(pybts.Node):

    def __init__(self, gpu):
        super().__init__(name=gpu.name)
        self.gpu = gpu

    def to_data(self):
        return {
            'ID'          : self.gpu.id,
            'Load'        : f'{self.gpu.load * 100}%',
            'Free Memory' : f'{self.gpu.memoryFree}MB',
            'Used Memory' : f'{self.gpu.memoryUsed}MB',
            'Total Memory': f'{self.gpu.memoryTotal}MB',
            'Temperature' : f'{self.gpu.temperature} °C'
        }

    def update(self):
        if self.gpu.load >= 0.8:
            return pybts.Status.FAILURE
        elif self.gpu.load >= 0.3:
            return pybts.Status.RUNNING
        else:
            return pybts.Status.SUCCESS


# 获取GPU列表
gpus = GPUtil.getGPUs()
root = pybts.Parallel(
        name='GPU',
        children=[
            GPUNode(gpu=gpu) for gpu in gpus
        ]
)

tree = pybts.Tree(root)
board = pybts.Board(tree=tree, log_dir='pybts-logs')
board.clear()

def gpu_track():
    gpus = GPUtil.getGPUs()

    for i, gpu in enumerate(gpus):
        root.children[i].gpu = gpu
    tree.tick()
    board.track()

if __name__ == '__main__':
    while True:
        gpu_track()
        time.sleep(1)
