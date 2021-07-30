#include <ATen/core/ivalue.h>

#include <torch/csrc/jit/codegen/cuda/fusion.h>
#include <torch/csrc/jit/codegen/cuda/scheduler/reduction_heuristic.h>

namespace torch {
namespace jit {
namespace fuser {
namespace cuda {

class SchedulerRuntimeInfo;

TORCH_CUDA_CU_API c10::optional<ReductionParams> getReductionHeuristics(
    Fusion* fusion,
    const at::ArrayRef<c10::IValue>& fusion_inputs);

TORCH_CUDA_CU_API c10::optional<ReductionParams> getReductionHeuristics(
    Fusion* fusion,
    SchedulerRuntimeInfo& runtime_info);

TORCH_CUDA_CU_API void scheduleReduction(
    Fusion* fusion,
    const ReductionParams& rparams);
} // namespace cuda
} // namespace fuser
} // namespace jit
} // namespace torch
