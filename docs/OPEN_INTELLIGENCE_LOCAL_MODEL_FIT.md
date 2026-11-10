# Local Model Fit Planner — offline AI resource compatibility worksheet

This is a deterministic, original public utility for exploring **hypothetical** RAM, storage and context limits when choosing an AI model for constrained devices. It does **not** inspect the phone, measure real RAM usage, run Ollama, infer model accuracy, benchmark latency or certify hardware compatibility. Every number is caller-supplied, and profiles in the demo are invented.

Run from the repository root with Python 3.10 or later (no subscriptions):

    python -m src.compound_intelligence.local_model_fit --demo
    python -m src.compound_intelligence.local_model_fit --constrained-demo
    python -m src.compound_intelligence.local_model_fit --demo --html /tmp/local-fit.html
    python -m unittest discover -s tests -p 'test_local_model_fit.py' -v

The demo has a fictional 3072 MiB RAM device with 512 MiB reserved, 2048 MiB available storage and a 4096-token minimum context. The fictional small model has an 850 MiB file, 1750 MiB estimated RAM and 8192-token context: it fits these supplied limits. The fictional large model does not fit its estimated RAM or file-storage limits. The constrained demo has no candidate that passes, by design.

Input schema: local-model-fit.v1. The JSON object contains a device with ram_mib, reserved_ram_mib, free_storage_mib and required_context_tokens, and an array of 1–100 models. Each candidate has a unique model_id, file_mib, estimated_runtime_ram_mib and context_capacity_tokens. All amounts are bounded integers. A result records RAM/storage/context headroom and explicit reasons for failed limits, rather than fabricating a performance score.

Exit codes: 0 means at least one model meets every supplied limit; 1 means input was valid but none meets them; 2 means malformed input or local HTML output failure. The HTML report is script-free, escaped and local only.

The estimated runtime RAM may omit KV-cache, framework memory, OS reserves, GPU offload and varying contexts; the model might still fail in reality. Real adoption requires a device-specific measured benchmark, model license review, test workload, privacy and usability check. This is source-level educational material, not a standalone repo, app or live deploy. Private Cortex, Commander, financial/trading infrastructure and client data remain excluded; extra recurring infrastructure cost R0.

Tracked by https://github.com/esheenj/compound-intelligence-starter/issues/43 .
