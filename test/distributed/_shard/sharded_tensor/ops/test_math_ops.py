# Owner(s): ["oncall: distributed"]

import torch
import torch.distributed._shard.sharded_tensor as sharded_tensor
import torch.distributed as dist

from torch.distributed._shard.sharding_spec import (
    ChunkShardingSpec,
    EnumerableShardingSpec,
    ShardMetadata
)
from torch.testing._internal.common_distributed import (
    requires_nccl,
    skip_if_lt_x_gpu,
)

from torch.testing._internal.distributed._shard.sharded_tensor import (
    ShardedTensorTestBase,
    with_comms,
)

class TestMathOps(ShardedTensorTestBase):
    @with_comms(init_rpc=False)
    @skip_if_lt_x_gpu(4)
    @requires_nccl()
    def test_basic_math_ops(self):
        import builtins
        ops = ["torch.add", "torch.sub", "torch.mul", "torch.div", "+", "-", "*"]

        def gen_code(python_op):
            src_lines = ['def f(lhs, rhs):']
            if "torch" in python_op:
                src_lines.append(f'  return {python_op}(lhs, rhs)\n')
            else:
                src_lines.append(f'  return lhs {python_op} rhs\n')

            return '\n'.join(src_lines)

        spec = ChunkShardingSpec(
            dim=0,
            placements=[
                "rank:0/cuda:0",
                "rank:1/cuda:1",
                "rank:2/cuda:2",
                "rank:3/cuda:3",
            ],
        )

        sharded_lhs = sharded_tensor.rand(spec, (12, 3))
        sharded_rhs = sharded_tensor.rand(spec, (12, 3))
        current_rank = dist.get_rank()
        global_lhs = torch.empty((12, 3)) if current_rank == 0 else None
        global_rhs = torch.empty((12, 3)) if current_rank == 0 else None
        sharded_lhs.gather(dst=0, out=global_lhs)
        sharded_rhs.gather(dst=0, out=global_rhs)

        res = sharded_lhs * 3
        for op in ops:
            g = {'torch': torch}
            code = gen_code(op)
            builtins.exec(code, g)

            # test basic math ops between ShardedTensors
            sharded_output = g["f"](sharded_lhs, sharded_rhs)
            output = torch.empty((12, 3)) if current_rank == 0 else None
            sharded_output.gather(dst=0, out=output)

            if current_rank == 0:
                global_output = g["f"](global_lhs, global_rhs)

                self.assertEqual(output, global_output)

            # test basic math ops between ShardedTensor and scalar
            sharded_output = g["f"](sharded_lhs, 3)
            output = torch.empty((12, 3)) if current_rank == 0 else None
            sharded_output.gather(dst=0, out=output)

            if current_rank == 0:
                global_output = g["f"](global_lhs, 3)

                self.assertEqual(output, global_output)



    @with_comms(init_rpc=False)
    @skip_if_lt_x_gpu(4)
    @requires_nccl()
    def test_math_ops_errors(self):
        spec = ChunkShardingSpec(
            dim=0,
            placements=[
                "rank:0/cuda:0",
                "rank:1/cuda:1",
                "rank:2/cuda:2",
                "rank:3/cuda:3",
            ],
        )
        sharded_lhs = sharded_tensor.rand(spec, (20, 3))
        sharded_rhs = sharded_tensor.rand(spec, (12, 3))

        with self.assertRaisesRegex(RuntimeError, 'Implicit broadcasting not supported'):
            torch.add(sharded_lhs, sharded_rhs)

        spec = EnumerableShardingSpec([
            ShardMetadata(
                shard_offsets=[0, 0],
                shard_sizes=[5, 5],
                placement="rank:0/cuda:0",
            ),
            ShardMetadata(
                shard_offsets=[0, 5],
                shard_sizes=[5, 5],
                placement="rank:1/cuda:1",
            ),
            ShardMetadata(
                shard_offsets=[5, 0],
                shard_sizes=[5, 5],
                placement="rank:2/cuda:2",
            ),
            ShardMetadata(
                shard_offsets=[5, 5],
                shard_sizes=[5, 5],
                placement="rank:3/cuda:3",
            )
        ])

        st = sharded_tensor.rand(spec, 10, 10)

        with self.assertRaisesRegex(TypeError, 'with ChunkShardingSpec supports'):
            torch.add(st, sharded_rhs)